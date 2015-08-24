var date_format = 'YYYY-MM-DD';
var time_format = 'hh:mm a';
var history_to_delete = [];

$.ajax({
    url: 'get_date_formats',
    type: 'GET',
    success: function(data) {
        date_format = data.date_format;
        time_format = data.time_format;
    }
});

history_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ history items",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"(filtered from _MAX_ total entries)",
        "emptyTable": "No data in table"
    },
    "pagingType": "bootstrap",
    "stateSave": true,
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [ 1, 'desc'],
    "autoWidth": false,
    "columnDefs": [
        {
            "targets": [0],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                $(td).html('<button class="btn btn-xs btn-warning" data-id="' + rowData['id'] + '"><i class="fa fa-trash-o fa-fw"></i> Delete</button>');
            },
            "width": "5%",
            "className": "delete-control no-wrap hidden",
            "searchable": false,
            "orderable": false
        },
        {
            "targets": [1],
            "data":"date",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['stopped'] === null) {
                    $(td).html('Currently watching...');
                } else {
                    $(td).html(moment(cellData,"X").format(date_format));
                }
            },
            "searchable": false,
            "width": "8%",
            "className": "no-wrap"
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
            "width": "8%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [3],
            "data": "ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData) {
                    if (isPrivateIP(cellData)) {
                        if (cellData != '') {
                            $(td).html(cellData);
                        } else {
                            $(td).html('n/a');
                        }
                    } else {
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal"><i class="fa fa-map-marker"></i>&nbsp' + cellData + '</a>');
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "8%",
            "className": "no-wrap hidden-md hidden-sm hidden-xs modal-control-ip"
        },
        {
            "targets": [4],
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
            "width": "15%",
            "className": "no-wrap hidden-md hidden-sm hidden-xs modal-control"
        },
        {
            "targets": [5],
            "data":"full_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var media_type = '';
                    var thumb_popover = '';
                    if (rowData['media_type'] === 'movie') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Movie"><i class="fa fa-film fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=80&height=120&fallback=poster" data-height="120">' + cellData + ' (' + rowData['year'] + ')</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&item_id=' + rowData['id'] + '"><div style="float: left;">' + media_type + '&nbsp' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'episode') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Episode"><i class="fa fa-television fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=80&height=120&fallback=poster" data-height="120">' + cellData + ' \
                            (S' + ('00' + rowData['parent_media_index']).slice(-2) + 'E' + ('00' + rowData['media_index']).slice(-2) + ')</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&item_id=' + rowData['id'] + '"><div style="float: left;" >' + media_type + '&nbsp' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'track') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=80&height=80&fallback=poster" data-height="80">' + cellData + ' (' + rowData['parent_title'] + ')</span>'
                        $(td).html('<div class="history-title"><div style="float: left;">' + media_type + '&nbsp' + thumb_popover + '</div></div>');
                    } else {
                        $(td).html('<a href="info?item_id=' + rowData['id'] + '">' + cellData + '</a>');
                    }
                }
            },
            "width": "35%"
        },
        {
            "targets": [6],
            "data":"started",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null) {
                    $(td).html('n/a');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [7],
            "data":"paused_counter",
            "render": function ( data, type, full ) {
                if (data !== null) {
                    return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
                } else {
                    return '0 mins';
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap hidden-md hidden-sm hidden-xs"
        },
        {
            "targets": [8],
            "data":"stopped",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null) {
                    $(td).html('n/a');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [9],
            "data":"duration",
            "render": function ( data, type, full ) {
                if (data !== null) {
                    return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
                } else {
                    return data;
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [10],
            "data":"percent_complete",
            "render": function ( data, type, full ) {
                if (data > 80) {
                    return '<span class="watched-tooltip" data-toggle="tooltip" title="Watched"><i class="fa fa-lg fa-circle"></i></span>'
                } else if (data > 40) {
                    return '<span class="watched-tooltip" data-toggle="tooltip" title="Partial"><i class="fa fa-lg fa-adjust fa-rotate-180"></i></span>'
                } else {
                    return '<span class="watched-tooltip" data-toggle="tooltip" title="Unwatched"><i class="fa fa-lg fa-circle-o"></i></span>'
                }
            },
            "searchable": false,
            "orderable": false,
            "className": "no-wrap hidden-md hidden-sm hidden-xs",
            "width": "1%"
        },
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('.transcode-tooltip').tooltip();
        $('.media-type-tooltip').tooltip();
        $('.watched-tooltip').tooltip();
        $('.thumb-tooltip').popover({
            html: true,
            trigger: 'hover',
            placement: 'right',
            content: function () {
                return '<div style="background-image: url(' + $(this).data('img') + '); width: 80px; height: ' + $(this).data('height') + 'px;" />';
            }
        });

        if ($('#row-edit-mode').hasClass('active')) {
            $('.delete-control').each(function() {
                $(this).removeClass('hidden');
            });
        }
    },
    "preDrawCallback": function(settings) {
        var msg = "<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData) {
        if ($.inArray(rowData['id'], history_to_delete) !== -1) {
            $(row).find('button[data-id="' + rowData['id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
    }
}

$('#history_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    function showStreamDetails() {
        $.ajax({
            url: 'get_stream_data',
            data: {row_id: rowData['id'], user: rowData['friendly_name']},
            cache: false,
            async: true,
            complete: function(xhr, status) {
                $("#info-modal").html(xhr.responseText);
            }
        });
    }
    showStreamDetails();
});

$('#history_table').on('click', 'td.modal-control-ip', function () {
    var tr = $(this).parents('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    function getUserLocation(ip_address) {
        if (isPrivateIP(ip_address)) {
            return "n/a"
        } else {
            $.ajax({
                url: 'get_ip_address_details',
                data: {ip_address: ip_address},
                async: true,
                complete: function(xhr, status) {
                    $("#ip-info-modal").html(xhr.responseText);
                }
            });
        }
    }
    getUserLocation(rowData['ip_address']);
});

$('#history_table').on('click', 'td.delete-control > button', function () {
    var tr = $(this).parents('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    var index = $.inArray(rowData['id'], history_to_delete);
    if (index === -1) {
        history_to_delete.push(rowData['id']);
    } else {
        history_to_delete.splice(index, 1);
    }
    $(this).toggleClass('btn-warning').toggleClass('btn-danger');
});