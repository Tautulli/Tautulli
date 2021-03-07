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
        "info": "Showing _START_ to _END_ of _TOTAL_ history items",
        "infoEmpty": "Showing 0 to 0 of 0 entries",
        "infoFiltered": "",
        "emptyTable": "No data in table",
        "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "pagingType": "simple_numbers",
    "stateSave": false,
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "lengthChange": false,
    "autoWidth": false,
    "order": [0, 'desc'],
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
            "width": "10%",
            "className": "no-wrap",
            "searchable": false
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
            "width": "10%",
            "className": "no-wrap",
            "searchable": false
        },
        {
            "targets": [2],
            "data":"friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['user_id']) {
                        $(td).html('<a href="' + page('user', rowData['user_id']) + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="' + page('user', null, rowData['user']) + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
            "width": "15%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data":"player",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var transcode_dec = '';
                    if (rowData['transcode_decision'] === 'transcode') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Transcode"><i class="fa fa-server fa-fw"></i></span>';
                    } else if (rowData['transcode_decision'] === 'copy') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Stream"><i class="fa fa-stream fa-fw"></i></span>';
                    } else if (rowData['transcode_decision'] === 'direct play') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Play"><i class="fa fa-play-circle fa-fw"></i></span>';
                    }
                    $(td).html('<div><a href="#" data-target="#info-modal" data-toggle="modal"><div style="float: left;">' + transcode_dec + '&nbsp' + cellData + '</div></a></div>');
                }
            },
            "width": "25%",
            "className": "no-wrap modal-control"
        },
        {
            "targets": [4],
            "data":"full_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var icon = '';
                    var icon_title = '';
                    var parent_info = '';
                    var media_type = '';
                    var thumb_popover = '';
                    var fallback = (rowData['live']) ? 'poster-live' : 'poster';
                    if (rowData['media_type'] === 'movie') {
                        icon = (rowData['live']) ? 'fa-broadcast-tower' : 'fa-film';
                        icon_title = (rowData['live']) ? 'Live TV' : 'Movie';
                        if (rowData['year']) { parent_info = ' (' + rowData['year'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="' + icon_title + '"><i class="fa ' + icon + ' fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, fallback) + '" data-height="120" data-width="80">' + cellData + parent_info + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key'], rowData['guid'], true, rowData['live']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'episode') {
                        icon = (rowData['live']) ? 'fa-broadcast-tower' : 'fa-television';
                        icon_title = (rowData['live']) ? 'Live TV' : 'Episode';
                        if (!isNaN(parseInt(rowData['parent_media_index'])) && !isNaN(parseInt(rowData['media_index']))) { parent_info = ' (' + short_season(rowData['parent_title']) + ' &middot; E' + rowData['media_index'] + ')'; }
                        else if (rowData['live'] && rowData['originally_available_at']) { parent_info = ' (' + rowData['originally_available_at'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="' + icon_title + '"><i class="fa ' + icon + ' fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, fallback) + '" data-height="120" data-width="80">' + cellData + parent_info + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key'], rowData['guid'], true, rowData['live']) + '"><div style="float: left;" >' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'track') {
                        if (rowData['parent_title']) { parent_info = ' (' + rowData['parent_title'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 300, null, null, null, 'cover') + '" data-height="80" data-width="80">' + cellData + parent_info + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key'], rowData['guid'], true, rowData['live']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else {
                        $(td).html('<a href="' + page('info', rowData['rating_key']) + '">' + cellData + '</a>');
                    }
                }
            },
            "width": "40%",
            "className": "datatable-wrap"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('body').tooltip({
            selector: '[data-toggle="tooltip"]',
            container: 'body'
        });
        $('body').popover({
            selector: '[data-toggle="popover"]',
            html: true,
            sanitize: false,
            container: '#history-modal',
            trigger: 'hover',
            placement: 'right',
            template: '<div class="popover history-thumbnail-popover" role="tooltip"><div class="arrow" style="top: 50%;"></div><div class="popover-content"></div></div>',
            content: function () {
                return '<div class="history-thumbnail" style="background-image: url(' + $(this).data('img') + '); height: ' + $(this).data('height') + 'px; width: ' + $(this).data('width') + 'px;" />';
            }
        });
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
    }
}

$('.history_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = history_table.row(tr);
    var rowData = row.data();

    function showStreamDetails() {
        $.ajax({
            url: 'get_stream_data',
            data: { row_id: rowData['row_id'], user: rowData['friendly_name'] },
            cache: false,
            async: true,
            complete: function (xhr, status) {
                $("#info-modal").html(xhr.responseText);
            }
        });
    }
    showStreamDetails();
});