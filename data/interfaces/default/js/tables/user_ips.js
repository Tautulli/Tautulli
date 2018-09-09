user_ip_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ results",
        "infoEmpty": "Showing 0 to 0 of 0 entries",
        "infoFiltered": "(filtered from _MAX_ total entries)",
        "emptyTable": "No data in table",
        "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "stateSave": true,
    "stateDuration": 0,
    "pagingType": "full_numbers",
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [ 0, 'desc'],
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data":"last_seen",
            "render": function ( data, type, full ) {
                return moment(data, "X").fromNow();
            },
            "searchable": false,
            "width": "15%",
            "className": "no-wrap"
        },
        {
            "targets": [1],
            "data": "ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData) {
                    isPrivateIP(cellData).then(function () {
                        $(td).html(cellData || 'n/a');
                    }, function () {
                        external_ip = '<span class="external-ip-tooltip" data-toggle="tooltip" title="External IP"><i class="fa fa-map-marker fa-fw"></i></span>';
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal">' + external_ip + cellData + '</a>');
                    });
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "15%",
            "className": "no-wrap modal-control-ip"
        },
        {
            "targets": [2],
            "data": "platform",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "15%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "player",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var transcode_dec = '';
                    if (rowData['transcode_decision'] === 'transcode') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Transcode"><i class="fa fa-server fa-fw"></i></span>';
                    } else if (rowData['transcode_decision'] === 'copy') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Stream"><i class="fa fa-video-camera fa-fw"></i></span>';
                    } else if (rowData['transcode_decision'] === 'direct play') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Play"><i class="fa fa-play-circle fa-fw"></i></span>';
                    }
                    $(td).html('<div><a href="#" data-target="#info-modal" data-toggle="modal"><div style="float: left;">' + transcode_dec + '&nbsp;' + cellData + '</div></a></div>');
                }
            },
            "width": "15%",
            "className": "no-wrap modal-control"
        },
        {
            "targets": [4],
            "data": "last_played",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var parent_info = '';
                    var media_type = '';
                    var thumb_popover = '';
                    if (rowData['media_type'] === 'movie') {
                        if (rowData['year']) { parent_info = ' (' + rowData['year'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Movie"><i class="fa fa-film fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=450&fallback=poster" data-height="120" data-width="80">' + cellData + parent_info + '</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'episode') {
                        if (rowData['parent_media_index'] && rowData['media_index']) { parent_info = ' (S' + rowData['parent_media_index'] + '&middot; E' + rowData['media_index'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Episode"><i class="fa fa-television fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=450&fallback=poster" data-height="120" data-width="80">' + cellData + parent_info + '</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;" >' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'track') {
                        if (rowData['parent_title']) { parent_info = ' (' + rowData['parent_title'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=300&fallback=cover" data-height="80" data-width="80">' + cellData + parent_info + '</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type']) {
                        $(td).html('<a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('n/a');
                    }
                }
            },
            "width": "30%",
            "className": "datatable-wrap"
        },
        {
            "targets": [5],
            "data": "play_count",
            "searchable": false,
            "width": "10%",
            "className": "no-wrap"
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
            container: 'body',
            trigger: 'hover',
            placement: 'right',
            template: '<div class="popover history-thumbnail-popover" role="tooltip"><div class="arrow" style="top: 50%;"></div><div class="popover-content"></div></div>',
            content: function () {
                return '<div class="history-thumbnail" style="background-image: url(' + $(this).data('img') + '); height: ' + $(this).data('height') + 'px;" />';
            }
        });

    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
    }
}

$('.user_ip_table').on('mouseenter', 'td.modal-control span', function () {
    $(this).tooltip();
});

$('.user_ip_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = user_ip_table.row(tr);
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

$('.user_ip_table').on('click', 'td.modal-control-ip', function () {
    var tr = $(this).parents('tr');
    var row = user_ip_table.row( tr );
    var rowData = row.data();

    $.get('get_ip_address_details', {
        ip_address: rowData['ip_address']
    }).then(function (jqXHR) {
        $("#ip-info-modal").html(jqXHR);
    });
});