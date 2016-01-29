var users_to_delete = [];
var users_to_purge = [];

users_list_table_options = {
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ active users",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"",
        "emptyTable": "No data in table",
    },
    "destroy": true,
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "order": [ 2, 'asc'],
    "autoWidth": true,
    "stateSave": false,
    "pagingType": "bootstrap",
    "columnDefs": [
        {
            "targets": [0],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                $(td).html('<div class="edit-user-toggles">' + 
                    '<button class="btn btn-xs btn-warning delete-user" data-id="' + rowData['user_id'] + '" data-toggle="button"><i class="fa fa-trash-o fa-fw"></i> Delete</button>&nbsp' +
                    '<button class="btn btn-xs btn-warning purge-user" data-id="' + rowData['user_id'] + '" data-toggle="button"><i class="fa fa-eraser fa-fw"></i> Purge</button>&nbsp&nbsp&nbsp' +
                    '<input type="checkbox" id="do_notify-' + rowData['user_id'] + '" name="do_notify" value="1" ' + rowData['do_notify'] + '><label class="edit-tooltip" for="do_notify-' + rowData['user_id'] + '" data-toggle="tooltip" title="Toggle Notifications"><i class="fa fa-bell fa-lg fa-fw"></i></label>&nbsp' +
                    '<input type="checkbox" id="keep_history-' + rowData['user_id'] + '" name="keep_history" value="1" ' + rowData['keep_history'] + '><label class="edit-tooltip" for="keep_history-' + rowData['user_id'] + '" data-toggle="tooltip" title="Toggle History"><i class="fa fa-history fa-lg fa-fw"></i></label>&nbsp' +
                    '</div>');
            },
            "width": "7%",
            "className": "edit-control no-wrap hidden",
            "searchable": false,
            "orderable": false
        },
        {
            "targets": [1],
            "data": "user_thumb",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === '') {
                    $(td).html('<a href="user?user_id=' + rowData['user_id'] + '"><div class="users-poster-face" style="background-image: url(interfaces/default/images/gravatar-default-80x80.png);"></div></a>');
                } else {
                    $(td).html('<a href="user?user_id=' + rowData['user_id'] + '"><div class="users-poster-face" style="background-image: url(' + rowData['user_thumb'] + ');"></div></a>');
                }
            },
            "orderable": false,
            "searchable": false,
            "width": "5%",
            "className": "users-thumbs"
        },
        {
            "targets": [2],
            "data": "friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html('<div class="edit-user-name" data-id="' + rowData['user_id'] + '">' +
                        '<a href="user?user_id=' + rowData['user_id'] + '">' + cellData + '</a>' +
                        '<input type="text" class="hidden" value="' + cellData + '">' +
                        '</div>');
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "10%",
            "className": "edit-user-control no-wrap"
        },
        {
            "targets": [3],
            "data": "last_seen",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(moment(cellData, "X").fromNow());
                } else {
                    $(td).html("never");
                }
            },
            "searchable": false,
            "width": "10%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [4],
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
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal"><span data-toggle="ip-tooltip" data-placement="left" title="IP Address Info" id="ip-info"><i class="fa fa-map-marker"></i></span>&nbsp' + cellData + '</a>');
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "10%",
            "className": "no-wrap hidden-md hidden-sm hidden-xs modal-control-ip"
        },
        {
            "targets": [5],
            "data": "platform",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "10%",
            "className": "no-wrap hidden-md hidden-sm hidden-xs modal-control"
        },
        {
            "targets": [6],
            "data":"player",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var transcode_dec = '';
                    if (rowData['video_decision'] === 'transcode' || rowData['audio_decision'] === 'transcode') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Transcode"><i class="fa fa-server fa-fw"></i></span>';
                    } else if (rowData['video_decision'] === 'copy' || rowData['audio_decision'] === 'copy') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Stream"><i class="fa fa-video-camera fa-fw"></i></span>';
                    } else if (rowData['video_decision'] === 'direct play' || rowData['audio_decision'] === 'direct play') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Play"><i class="fa fa-play-circle fa-fw"></i></span>';
                    }
                    $(td).html('<div><a href="#" data-target="#info-modal" data-toggle="modal"><div style="float: left;">' + transcode_dec + '&nbsp;' + cellData + '</div></a></div>');
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "15%",
            "className": "no-wrap hidden-md hidden-sm hidden-xs modal-control"
        },
        {
            "targets": [7],
            "data":"last_played",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
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
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=300&fallback=poster" data-height="80" data-width="80">' + cellData + parent_info + '</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type']) {
                        $(td).html('<a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "30%",
            "className": "hidden-sm hidden-xs"
        },
        {
            "targets": [8],
            "data": "plays",
            "searchable": false,
            "width": "10%"
        }

    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        //$('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('.purge-tooltip').tooltip();
        $('.edit-tooltip').tooltip();
        $('.transcode-tooltip').tooltip();
        $('.media-type-tooltip').tooltip();
        $('.watched-tooltip').tooltip();
        $('.thumb-tooltip').popover({
            html: true,
            trigger: 'hover',
            placement: 'right',
            template: '<div class="popover history-thumbnail-popover" role="tooltip"><div class="arrow" style="top: 50%;"></div><div class="popover-content"></div></div>',
            content: function () {
                return '<div class="history-thumbnail" style="background-image: url(' + $(this).data('img') + '); height: ' + $(this).data('height') + 'px; width: ' + $(this).data('width') + 'px;" />';
            }
        });

        if ($('#row-edit-mode').hasClass('active')) {
            $('.edit-control').each(function () {
                $(this).removeClass('hidden');
            });
        }
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData) {
        if ($.inArray(rowData['user_id'], users_to_delete) !== -1) {
            $(row).find('button.delete-user[data-id="' + rowData['user_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
        if ($.inArray(rowData['user_id'], users_to_purge) !== -1) {
            $(row).find('button.purge-user[data-id="' + rowData['user_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
    }
}

$('#users_list_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
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

$('#users_list_table').on('click', 'td.modal-control-ip', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
    var rowData = row.data();

    function getUserLocation(ip_address) {
        if (isPrivateIP(ip_address)) {
            return "n/a"
        } else {
            $.ajax({
                url: 'get_ip_address_details',
                data: { ip_address: ip_address },
                async: true,
                complete: function (xhr, status) {
                    $("#ip-info-modal").html(xhr.responseText);
                }
            });
        }
    }

    getUserLocation(rowData['ip_address']);
});

$('#users_list_table').on('change', 'td.edit-control > .edit-user-toggles > input, td.edit-user-control > .edit-user-name > input', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
    var rowData = row.data();

    var do_notify = 0;
    var keep_history = 0;
    if ($('#do_notify-' + rowData['user_id']).is(':checked')) {
        do_notify = 1;
    }
    if ($('#keep_history-' + rowData['user_id']).is(':checked')) {
        keep_history = 1;
    }

    friendly_name = tr.find('td.edit-user-control > .edit-user-name > input').val();

    $.ajax({
        url: 'edit_user',
        data: {
            user_id: rowData['user_id'],
            friendly_name: friendly_name,
            do_notify: do_notify,
            keep_history: keep_history,
            thumb: rowData['user_thumb']
        },
        cache: false,
        async: true,
        success: function (data) {
            var msg = "User updated";
            showMsg(msg, false, true, 2000);
        }
    });
});

$('#users_list_table').on('click', 'td.edit-control > .edit-user-toggles > button.delete-user', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
    var rowData = row.data();

    var index_delete = $.inArray(rowData['user_id'], users_to_delete);
    var index_purge = $.inArray(rowData['user_id'], users_to_purge);

    if (index_delete === -1) {
        users_to_delete.push(rowData['user_id']);
        if (index_purge === -1) {
            tr.find('button.purge-user').click();
        }
    } else {
        users_to_delete.splice(index_delete, 1);
        if (index_purge != -1) {
            tr.find('button.purge-user').click();
        }
    }
    $(this).toggleClass('btn-warning').toggleClass('btn-danger');

});

$('#users_list_table').on('click', 'td.edit-control > .edit-user-toggles > button.purge-user', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
    var rowData = row.data();

    var index_delete = $.inArray(rowData['user_id'], users_to_delete);
    var index_purge = $.inArray(rowData['user_id'], users_to_purge);

    if (index_purge === -1) {
        users_to_purge.push(rowData['user_id']);
    } else {
        users_to_purge.splice(index_purge, 1);
        if (index_delete != -1) {
            tr.find('button.delete-user').click();
        }
    }
    $(this).toggleClass('btn-warning').toggleClass('btn-danger');
});