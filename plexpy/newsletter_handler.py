#  This file is part of Tautulli.
#
#  Tautulli is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Tautulli is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with Tautulli.  If not, see <http://www.gnu.org/licenses/>.

import os
import time

from apscheduler.triggers.cron import CronTrigger
import email.utils

import plexpy
import database
import logger
import newsletters


NEWSLETTER_SCHED = None


def add_newsletter_each(newsletter_id=None, notify_action=None, **kwargs):
    if not notify_action:
        logger.debug("Tautulli NewsletterHandler :: Notify called but no action received.")
        return

    data = {'newsletter': True,
            'newsletter_id': newsletter_id,
            'notify_action': notify_action}
    data.update(kwargs)
    plexpy.NOTIFY_QUEUE.put(data)


def schedule_newsletters(newsletter_id=None):
    newsletters_list = newsletters.get_newsletters(newsletter_id=newsletter_id)

    for newsletter in newsletters_list:
        newsletter_job_name = '{} (newsletter_id {})'.format(newsletter['agent_label'], newsletter['id'])

        if newsletter['active']:
            schedule_newsletter_job('newsletter-{}'.format(newsletter['id']), name=newsletter_job_name,
                                    func=add_newsletter_each, args=[newsletter['id'], 'on_cron'], cron=newsletter['cron'])
        else:
            schedule_newsletter_job('newsletter-{}'.format(newsletter['id']), name=newsletter_job_name,
                                    remove_job=True)


def schedule_newsletter_job(newsletter_job_id, name='', func=None, remove_job=False, args=None, cron=None):
    if NEWSLETTER_SCHED.get_job(newsletter_job_id):
        if remove_job:
            NEWSLETTER_SCHED.remove_job(newsletter_job_id)
            logger.info("Tautulli NewsletterHandler :: Removed scheduled newsletter: %s" % name)
        else:
            NEWSLETTER_SCHED.reschedule_job(
                newsletter_job_id, args=args, trigger=CronTrigger.from_crontab(cron))
            logger.info("Tautulli NewsletterHandler :: Re-scheduled newsletter: %s" % name)
    elif not remove_job:
        NEWSLETTER_SCHED.add_job(
            func, args=args, id=newsletter_job_id, trigger=CronTrigger.from_crontab(cron))
        logger.info("Tautulli NewsletterHandler :: Scheduled newsletter: %s" % name)


def notify(newsletter_id=None, notify_action=None, **kwargs):
    logger.info("Tautulli NewsletterHandler :: Preparing newsletter for newsletter_id %s." % newsletter_id)

    newsletter_config = newsletters.get_newsletter_config(newsletter_id=newsletter_id)

    if not newsletter_config:
        return

    if notify_action in ('test', 'api'):
        subject = kwargs.pop('subject', None) or newsletter_config['subject']
        body = kwargs.pop('body', None) or newsletter_config['body']
        message = kwargs.pop('message', None) or newsletter_config['message']
    else:
        subject = newsletter_config['subject']
        body = newsletter_config['body']
        message = newsletter_config['message']

    email_msg_id = email.utils.make_msgid()
    email_reply_msg_id = get_last_newsletter_email_msg_id(newsletter_id=newsletter_id, notify_action=notify_action)

    newsletter_agent = newsletters.get_agent_class(newsletter_id=newsletter_id,
                                                   newsletter_id_name=newsletter_config['id_name'],
                                                   agent_id=newsletter_config['agent_id'],
                                                   config=newsletter_config['config'],
                                                   email_config=newsletter_config['email_config'],
                                                   subject=subject,
                                                   body=body,
                                                   message=message,
                                                   email_msg_id=email_msg_id,
                                                   email_reply_msg_id=email_reply_msg_id
                                                   )

    # Set the newsletter state in the db
    newsletter_log_id = set_notify_state(newsletter=newsletter_config,
                                         notify_action=notify_action,
                                         subject=newsletter_agent.subject_formatted,
                                         body=newsletter_agent.body_formatted,
                                         message=newsletter_agent.message_formatted,
                                         filename=newsletter_agent.filename_formatted,
                                         start_date=newsletter_agent.start_date.format('YYYY-MM-DD'),
                                         end_date=newsletter_agent.end_date.format('YYYY-MM-DD'),
                                         start_time=newsletter_agent.start_time,
                                         end_time=newsletter_agent.end_time,
                                         newsletter_uuid=newsletter_agent.uuid,
                                         email_msg_id=email_msg_id)

    # Send the notification
    success = newsletter_agent.send()

    if success:
        set_notify_success(newsletter_log_id)
        return True


def set_notify_state(newsletter, notify_action, subject, body, message, filename,
                     start_date, end_date, start_time, end_time, newsletter_uuid, email_msg_id):

    if newsletter and notify_action:
        db = database.MonitorDatabase()

        keys = {'timestamp': int(time.time()),
                'uuid': newsletter_uuid}

        values = {'newsletter_id': newsletter['id'],
                  'agent_id': newsletter['agent_id'],
                  'agent_name': newsletter['agent_name'],
                  'notify_action': notify_action,
                  'subject_text': subject,
                  'body_text': body,
                  'message_text': message,
                  'start_date': start_date,
                  'end_date': end_date,
                  'start_time': start_time,
                  'end_time': end_time,
                  'email_msg_id': email_msg_id,
                  'filename': filename}

        db.upsert(table_name='newsletter_log', key_dict=keys, value_dict=values)
        return db.last_insert_id()
    else:
        logger.error("Tautulli NewsletterHandler :: Unable to set notify state.")


def set_notify_success(newsletter_log_id):
    keys = {'id': newsletter_log_id}
    values = {'success': 1}

    db = database.MonitorDatabase()
    db.upsert(table_name='newsletter_log', key_dict=keys, value_dict=values)


def get_last_newsletter_email_msg_id(newsletter_id, notify_action):
    db = database.MonitorDatabase()

    result = db.select_single('SELECT email_msg_id FROM newsletter_log '
                              'WHERE newsletter_id = ? AND notify_action = ? AND success = 1 '
                              'ORDER BY timestamp DESC LIMIT 1', [newsletter_id, notify_action])

    if result:
        return result['email_msg_id']


def get_newsletter(newsletter_uuid=None, newsletter_id_name=None):
    db = database.MonitorDatabase()

    if newsletter_uuid:
        result = db.select_single('SELECT start_date, end_date, uuid, filename FROM newsletter_log '
                                  'WHERE uuid = ?', [newsletter_uuid])
    elif newsletter_id_name:
        result = db.select_single('SELECT start_date, end_date, uuid, filename FROM newsletter_log '
                                  'JOIN newsletters ON newsletters.id = newsletter_log.newsletter_id '
                                  'WHERE id_name = ? AND notify_action != "test" '
                                  'ORDER BY timestamp DESC LIMIT 1', [newsletter_id_name])
    else:
        result = None

    if result:
        newsletter_uuid = result['uuid']
        start_date = result['start_date']
        end_date = result['end_date']
        newsletter_file = result['filename'] or 'newsletter_%s-%s_%s.html' % (start_date.replace('-', ''),
                                                                              end_date.replace('-', ''),
                                                                              newsletter_uuid)

        newsletter_folder = plexpy.CONFIG.NEWSLETTER_DIR or os.path.join(plexpy.DATA_DIR, 'newsletters')
        newsletter_file_fp = os.path.join(newsletter_folder, newsletter_file)

        if newsletter_file in os.listdir(newsletter_folder):
            try:
                with open(newsletter_file_fp, 'r') as n_file:
                    newsletter = n_file.read()
                return newsletter
            except OSError as e:
                logger.error("Tautulli NewsletterHandler :: Failed to retrieve newsletter '%s': %s" % (newsletter_uuid, e))
        else:
            logger.warn("Tautulli NewsletterHandler :: Newsletter file '%s' is missing." % newsletter_file)
