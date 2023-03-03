###############################################################################
# Google Analytics 4 Measurement Protocol for Python
# Copyright (c) 2022, Adswerve
#
# This project is free software, distributed under the BSD license.
# Adswerve offers consulting and integration services if your firm needs
# assistance in strategy, implementation, or auditing existing work.
###############################################################################

import json
import logging
import urllib.request
import time
import datetime
import random
from ga4mp.utils import params_dict
from ga4mp.event import Event
from ga4mp.store import BaseStore, DictStore

import os, sys
sys.path.append(
    os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BaseGa4mp(object):
    """
    Parent class that provides an interface for sending data to Google Analytics, supporting the GA4 Measurement Protocol.

    Parameters
    ----------
    api_secret : string
        Generated through the Google Analytics UI. To create a new secret, navigate in the Google Analytics UI to: Admin > Data Streams >
        [choose your stream] > Measurement Protocol API Secrets > Create

    See Also
    --------

    * Measurement Protocol (Google Analytics 4): https://developers.google.com/analytics/devguides/collection/protocol/ga4

    Examples
    --------
    # Initialize tracking object for gtag usage
    >>> ga = gtagMP(api_secret = "API_SECRET", measurement_id = "MEASUREMENT_ID", client_id="CLIENT_ID")

    # Initialize tracking object for Firebase usage
    >>> ga = firebaseMP(api_secret = "API_SECRET", firebase_app_id = "FIREBASE_APP_ID", app_instance_id="APP_INSTANCE_ID")

    # Build an event
    >>> event_type = 'new_custom_event'
    >>> event_parameters = {'parameter_key_1': 'parameter_1', 'parameter_key_2': 'parameter_2'}
    >>> event = {'name': event_type, 'params': event_parameters }
    >>> events = [event]

    # Send a custom event to GA4 immediately
    >>> ga.send(events)

    # Postponed send of a custom event to GA4
    >>> ga.send(events, postpone=True)
    >>> ga.postponed_send()
    """

    def __init__(self, api_secret, store: BaseStore = None):
        self._initialization_time = time.time() # used for both session_id and calculating engagement time
        self.api_secret = api_secret
        self._event_list = []
        assert store is None or isinstance(store, BaseStore), "if supplied, store must be an instance of BaseStore"
        self.store = store or DictStore()
        self._check_store_requirements()
        self._base_domain = "https://www.google-analytics.com/mp/collect"
        self._validation_domain = "https://www.google-analytics.com/debug/mp/collect"

    def _check_store_requirements(self):
        # Store must contain "session_id" and "last_interaction_time_msec" in order for tracking to work properly.
        if self.store.get_session_parameter("session_id") is None:
            self.store.set_session_parameter(name="session_id", value=int(self._initialization_time))
        # Note: "last_interaction_time_msec" factors into the required "engagement_time_msec" event parameter.
        self.store.set_session_parameter(name="last_interaction_time_msec", value=int(self._initialization_time * 1000))

    def create_new_event(self, name):
        return Event(name=name)

    def send(self, events, validation_hit=False, postpone=False, date=None):
        """
        Method to send an http post request to google analytics with the specified events.

        Parameters
        ----------
        events : List[Dict]
            A list of dictionaries of the events to be sent to Google Analytics. The list of dictionaries should adhere
            to the following format:

            [{'name': 'level_end',
            'params' : {'level_name': 'First',
                        'success': 'True'}
            },
            {'name': 'level_up',
            'params': {'character': 'John Madden',
                        'level': 'First'}
            }]

        validation_hit : bool, optional
            Boolean to depict if events should be tested against the Measurement Protocol Validation Server, by default False
        postpone : bool, optional
            Boolean to depict if provided event list should be postponed, by default False
        date : datetime
            Python datetime object for sending a historical event at the given date. Date cannot be in the future.
        """

        # check for any missing or invalid parameters among automatically collected and recommended event types
        self._check_params(events)
        self._check_date_not_in_future(date)
        self._add_session_id_and_engagement_time(events)

        if postpone is True:
            # build event list to send later
            for event in events:
                event["_timestamp_micros"] = self._get_timestamp(time.time())
                self._event_list.append(event)
        else:
            # batch events into sets of 25 events, the maximum allowed.
            batched_event_list = [
                events[event : event + 25] for event in range(0, len(events), 25)
            ]
            # send http post request
            self._http_post(
                batched_event_list, validation_hit=validation_hit, date=date
            )

    def postponed_send(self):
        """
        Method to send the events provided to Ga4mp.send(events,postpone=True)
        """

        for event in self._event_list:
            self._http_post([event], postpone=True)

        # clear event_list for future use
        self._event_list = []

    def append_event_to_params_dict(self, new_name_and_parameters):

        """
        Method to append event name and parameters key-value pairing(s) to parameters dictionary.

        Parameters
        ----------
        new_name_and_parameters : Dict
            A dictionary with one key-value pair representing a new type of event to be sent to Google Analytics.
            The dictionary should adhere to the following format:

            {'new_name': ['new_param_1', 'new_param_2', 'new_param_3']}
        """

        params_dict.update(new_name_and_parameters)

    def _http_post(self, batched_event_list, validation_hit=False, postpone=False, date=None):
        """
        Method to send http POST request to google-analytics.

        Parameters
        ----------
        batched_event_list : List[List[Dict]]
            List of List of events. Places initial event payload into a list to send http POST in batches.
        validation_hit : bool, optional
            Boolean to depict if events should be tested against the Measurement Protocol Validation Server, by default False
        postpone : bool, optional
            Boolean to depict if provided event list should be postponed, by default False
        date : datetime
            Python datetime object for sending a historical event at the given date. Date cannot be in the future.
            Timestamp micros supports up to 48 hours of backdating.
            If date is specified, postpone must be False or an assertion will be thrown.
        """
        self._check_date_not_in_future(date)
        status_code = None  # Default set to know if batch loop does not work and to bound status_code

        # set domain
        domain = self._base_domain
        if validation_hit is True:
            domain = self._validation_domain
        logger.info(f"Sending POST to: {domain}")

        # loop through events in batches of 25
        batch_number = 1
        for batch in batched_event_list:
            # url and request slightly differ by subclass
            url = self._build_url(domain=domain)
            request = self._build_request(batch=batch)
            self._add_user_props_to_hit(request)

            # make adjustments for postponed hit
            request["events"] = (
                {"name": batch["name"], "params": batch["params"]}
                if (postpone)
                else batch
            )

            if date is not None:
                logger.info(f"Setting event timestamp to: {date}")
                assert (
                    postpone is False
                ), "Cannot send postponed historical hit, ensure postpone=False"

                ts = self._datetime_to_timestamp(date)
                ts_micro = self._get_timestamp(ts)
                request["timestamp_micros"] = int(ts_micro)
                logger.info(f"Timestamp of request is: {request['timestamp_micros']}")

            if postpone:
                # add timestamp to hit
                request["timestamp_micros"] = batch["_timestamp_micros"]

            req = urllib.request.Request(url)
            req.add_header("Content-Type", "application/json; charset=utf-8")
            jsondata = json.dumps(request)
            json_data_as_bytes = jsondata.encode("utf-8")  # needs to be bytes
            req.add_header("Content-Length", len(json_data_as_bytes))
            result = urllib.request.urlopen(req, json_data_as_bytes)

            status_code = result.status
            logger.info(f"Batch Number: {batch_number}")
            logger.info(f"Status code: {status_code}")
            batch_number += 1

        return status_code

    def _check_params(self, events):

        """
        Method to check whether the provided event payload parameters align with supported parameters.

        Parameters
        ----------
        events : List[Dict]
            A list of dictionaries of the events to be sent to Google Analytics. The list of dictionaries should adhere
            to the following format:

            [{'name': 'level_end',
            'params' : {'level_name': 'First',
                        'success': 'True'}
            },
            {'name': 'level_up',
            'params': {'character': 'John Madden',
                        'level': 'First'}
            }]
        """

        # check to make sure it's a list of dictionaries with the right keys

        assert type(events) == list, "events should be a list"

        for event in events:

            assert isinstance(event, dict), "each event should be an instance of a dictionary"

            assert "name" in event, 'each event should have a "name" key'

            assert "params" in event, 'each event should have a "params" key'

        # check for any missing or invalid parameters

        for e in events:
            event_name = e["name"]
            event_params = e["params"]
            if event_name in params_dict.keys():
                for parameter in params_dict[event_name]:
                    if parameter not in event_params.keys():
                        logger.warning(
                            f"WARNING: Event parameters do not match event type.\nFor {event_name} event type, the correct parameter(s) are {params_dict[event_name]}.\nThe parameter '{parameter}' triggered this warning.\nFor a breakdown of currently supported event types and their parameters go here: https://support.google.com/analytics/answer/9267735\n"
                        )

    def _add_session_id_and_engagement_time(self, events):
        """
        Method to add the session_id and engagement_time_msec parameter to all events.
        """
        for event in events:
            current_time_in_milliseconds = int(time.time() * 1000)

            event_params = event["params"]
            if "session_id" not in event_params.keys():
                event_params["session_id"] = self.store.get_session_parameter("session_id")
            if "engagement_time_msec" not in event_params.keys():
                last_interaction_time = self.store.get_session_parameter("last_interaction_time_msec")
                event_params["engagement_time_msec"] = current_time_in_milliseconds - last_interaction_time if current_time_in_milliseconds > last_interaction_time else 0
                self.store.set_session_parameter(name="last_interaction_time_msec", value=current_time_in_milliseconds)

    def _add_user_props_to_hit(self, hit):

        """
        Method is a helper function to add user properties to outgoing hits.

        Parameters
        ----------
        hit : dict
        """

        for key in self.store.get_all_user_properties():
            try:
                if key in ["user_id", "non_personalized_ads"]:
                    hit.update({key: self.store.get_user_property(key)})
                else:
                    if "user_properties" not in hit.keys():
                        hit.update({"user_properties": {}})
                    hit["user_properties"].update(
                        {key: {"value": self.store.get_user_property(key)}}
                    )
            except:
                logger.info(f"Failed to add user property to outgoing hit: {key}")

    def _get_timestamp(self, timestamp):
        """
        Method returns UNIX timestamp in microseconds for postponed hits.

        Parameters
        ----------
        None
        """
        return int(timestamp * 1e6)

    def _datetime_to_timestamp(self, dt):
        """
        Private method to convert a datetime object into a timestamp

        Parameters
        ----------
        dt : datetime
            A datetime object in any format

        Returns
        -------
        timestamp
            A UNIX timestamp in milliseconds
        """
        return time.mktime(dt.timetuple())

    def _check_date_not_in_future(self, date):
        """
        Method to check that provided date is not in the future.

        Parameters
        ----------
        date : datetime
            Python datetime object
        """
        if date is None:
            pass
        else:
            assert (
                date <= datetime.datetime.now()
            ), "Provided date cannot be in the future"

    def _build_url(self, domain):
        raise NotImplementedError("Subclass should be using this function, but it was called through the base class instead.")

    def _build_request(self, batch):
        raise NotImplementedError("Subclass should be using this function, but it was called through the base class instead.")

class GtagMP(BaseGa4mp):
    """
    Subclass for users of gtag. See `Ga4mp` parent class for examples.

    Parameters
    ----------
    measurement_id : string
        The identifier for a Data Stream. Found in the Google Analytics UI under: Admin > Data Streams > [choose your stream] > Measurement ID (top-right)
    client_id : string
        A unique identifier for a client, representing a specific browser/device.
    """

    def __init__(self, api_secret, measurement_id, client_id,):
        super().__init__(api_secret)
        self.measurement_id = measurement_id
        self.client_id = client_id

    def _build_url(self, domain):
        return f"{domain}?measurement_id={self.measurement_id}&api_secret={self.api_secret}"

    def _build_request(self, batch):
        return {"client_id": self.client_id, "events": batch}

    def random_client_id(self):
        """
        Utility function for generating a new client ID matching the typical format of 10 random digits and the UNIX timestamp in seconds, joined by a period.
        """
        return "%0.10d" % random.randint(0,9999999999) + "." + str(int(time.time()))

class FirebaseMP(BaseGa4mp):
    """
    Subclass for users of Firebase. See `Ga4mp` parent class for examples.

    Parameters
    ----------
    firebase_app_id : string
        The identifier for a Firebase app. Found in the Firebase console under: Project Settings > General > Your Apps > App ID.
    app_instance_id : string
        A unique identifier for a Firebase app instance.
            * Android - getAppInstanceId() - https://firebase.google.com/docs/reference/android/com/google/firebase/analytics/FirebaseAnalytics#public-taskstring-getappinstanceid
            * Kotlin - getAppInstanceId() - https://firebase.google.com/docs/reference/kotlin/com/google/firebase/analytics/FirebaseAnalytics#getappinstanceid
            * Swift - appInstanceID() - https://firebase.google.com/docs/reference/swift/firebaseanalytics/api/reference/Classes/Analytics#appinstanceid
            * Objective-C - appInstanceID - https://firebase.google.com/docs/reference/ios/firebaseanalytics/api/reference/Classes/FIRAnalytics#+appinstanceid
            * C++ - GetAnalyticsInstanceId() - https://firebase.google.com/docs/reference/cpp/namespace/firebase/analytics#getanalyticsinstanceid
            * Unity - GetAnalyticsInstanceIdAsync() - https://firebase.google.com/docs/reference/unity/class/firebase/analytics/firebase-analytics#getanalyticsinstanceidasync
    """

    def __init__(self, api_secret, firebase_app_id, app_instance_id):
        super().__init__(api_secret)
        self.firebase_app_id = firebase_app_id
        self.app_instance_id = app_instance_id

    def _build_url(self, domain):
        return f"{domain}?firebase_app_id={self.firebase_app_id}&api_secret={self.api_secret}"

    def _build_request(self, batch):
        return {"app_instance_id": self.app_instance_id, "events": batch}