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
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var transcode_dec = '';
                    if (rowData['video_decision'] === 'transcode') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Transcode"><i class="fa fa-server fa-fw"></i></span>';
                    } else if (rowData['video_decision'] === 'copy') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Stream"><i class="fa fa-video-camera fa-fw"></i></span>';
                    } else if (rowData['video_decision'] === 'direct play' || rowData['video_decision'] === '') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Play"><i class="fa fa-play-circle fa-fw"></i></span>';
                    }
                    $(td).html('<div><a href="#" data-target="#info-modal" data-toggle="modal"><div style="float: left;">' + transcode_dec + '&nbsp' + cellData + '</div></a></div>');
                }
            },
            "className": "no-wrap hidden-sm hidden-xs modal-control"
        },
        {
            "targets": [4],
            "data":"full_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var media_type = '';
                    var thumb_popover = '';
                    if (rowData['media_type'] === 'movie') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Movie"><i class="fa fa-film fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=450&fallback=poster" data-height="120">' + cellData + ' (' + rowData['year'] + ')</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&item_id=' + rowData['id'] + '"><div style="float: left;">' + media_type + '&nbsp' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'episode') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Episode"><i class="fa fa-television fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=450&fallback=poster" data-height="120">' + cellData + ' \
                            (S' + rowData['parent_media_index'] + '&middot; E' + rowData['media_index'] + ')</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&item_id=' + rowData['id'] + '"><div style="float: left;" >' + media_type + '&nbsp' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'track') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=300&fallback=poster" data-height="80">' + cellData + ' (' + rowData['parent_title'] + ')</span>'
                        $(td).html('<div class="history-title"><div style="float: left;">' + media_type + '&nbsp' + thumb_popover + '</div></div>');
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

        // Create the tooltips.
        $('.transcode-tooltip').tooltip();
        $('.media-type-tooltip').tooltip();
        $('.thumb-tooltip').popover({
            html: true,
            trigger: 'hover',
            placement: 'right',
            content: function () {
                return '<div class="history-thumbnail" style="background-image: url(' + $(this).data('img') + '); height: ' + $(this).data('height') + 'px;" />';
            }
        });
    },
    "preDrawCallback": function(settings) {
        var msg = "<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>";
        showMsg(msg, false, false, 0)
    }
}

$('#history_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = history_table.row(tr);
    var rowData = row.data();

    function showStreamDetails() {
        $.ajax({
            url: 'get_stream_data',
            data: { row_id: rowData['id'], user: rowData['friendly_name'] },
            cache: false,
            async: true,
            complete: function (xhr, status) {
                $("#info-modal").html(xhr.responseText);
            }
        });
    }
    showStreamDetails();
});