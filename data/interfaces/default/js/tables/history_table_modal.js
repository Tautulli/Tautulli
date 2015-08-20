var date_format = 'YYYY-MM-DD';
var time_format = 'hh:mm a';

$.ajax({
    url: 'get_date_formats',
    type: 'GET',
    success: function(data) {
        date_format = data.date_format;
        time_format = data.time_format;
    }
});

history_table_modal_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "info":"Showing _START_ to _END_ of _TOTAL_ history items",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"",
        "emptyTable": "No data in table",
    },
    "pagingType": "bootstrap",
    "stateSave": false,
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "lengthChange": false,
    "order": [ 0, 'desc'],
    "columnDefs": [
        {
            "targets": [0],
            "data":"started",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null) {
                    $(td).html('Unknown');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "className": "no-wrap",
            "width": "5%"
        },
        {
            "targets": [1],
            "data":"stopped",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null) {
                    $(td).html('Unknown');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "className": "no-wrap",
            "width": "5%"
        },
        {
            "targets": [2],
            "data":"friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['user_id']) {
                        $(td).html('<a href="user?user_id=' + rowData['user_id'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="user?user=' + rowData['user'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [3],
            "data":"player",
            "className": "no-wrap hidden-sm hidden-xs modal-control"
        },
        {
            "targets": [4],
            "data":"full_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['media_type'] === 'movie' || rowData['media_type'] === 'episode') {
                        var transcode_dec = '';
                        if (rowData['video_decision'] === 'transcode') {
                            transcode_dec = '<i class="fa fa-server"></i>&nbsp';
                        }
                        $(td).html('<div><div style="float: left;"><a href="info?source=history&item_id=' + rowData['id'] + '">' + cellData + '</a></div><div style="float: right; text-align: right; padding-right: 5px;">' + transcode_dec + '<i class="fa fa-video-camera"></i></div></div>');
                    } else if (rowData['media_type'] === 'track') {
                        $(td).html('<div><div style="float: left;">' + cellData + '</div><div style="float: right; text-align: right; padding-right: 5px;"><i class="fa fa-music"></i></div></div>');
                    } else {
                        $(td).html('<a href="info?item_id=' + rowData['id'] + '">' + cellData + '</a>');
                    }
                }
            }
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();
    },
    "preDrawCallback": function(settings) {
        var msg = "<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>";
        showMsg(msg, false, false, 0)
    }
}