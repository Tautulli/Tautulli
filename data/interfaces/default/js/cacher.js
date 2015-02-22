// check if browser supports session storage, if not log error in console.
if(sessionStorage === null) console.log("Session storage not supported by this browser.");

// get cache object
var temp = sessionStorage.getItem('cacheObj');
var cacheObj = $.parseJSON(temp);

// create cache object if it doesn't exist
if (cacheObj === null) {
    var cacheObj = new Object();
}

// setCache function
// usage: setCache(unique_identifier, data_to_be_cached, minutes_to_remain_cached [optional, default = 60] )
function setCache(postId, postData, validityTime) {

    validityTime = typeof validityTime !== 'undefined' ? validityTime : 60;

    // get the current time
    var milliseconds = new Date().getTime();

    if (cacheObj.length > 0) {

        var objectExists = false;

        //check if we already have this data stored and is current
        for (var i = 0; i < cacheObj.length; i++) {
            if (cacheObj[i].postId === postId) {
                objectExists = true;
            }
        }
        // add the data to the object if it's not there already
        if (!objectExists) {
            cacheObj.push( { postId: postId, data: postData, expire: (milliseconds + (validityTime * 60 * 1000)) } );
            sessionStorage.setItem('cacheObj', JSON.stringify(cacheObj));
        }
    } else {
        cacheObj =  [ { postId: postId, data: postData, expire: (milliseconds + (validityTime * 60 * 1000)) } ];
        sessionStorage.setItem('cacheObj', JSON.stringify(cacheObj));
    }

};

// getCache function
// usage: getCache(unique_identifier)
function getCache(postId) {

    // get the current time
    var milliseconds = new Date().getTime();

    if (cacheObj.length > 0) {
        for (var i = 0; i < cacheObj.length; i++) {
            if (cacheObj[i].postId === postId) {
                // check if item has expired
                if (milliseconds < cacheObj[i].expire) {
                    return cacheObj[i].data;
                } else {
                    // if item expired then remove from cache object
                    console.log('Object expired, destroying.');
                    cacheObj.splice(i, 1);
                }
            }
        }
    }
    return false;
};