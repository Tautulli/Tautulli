var users_to_delete = [];
var users_to_purge = [];

function toggleEditNames() {
    if ($('.edit-control').hasClass('hidden')) {
        $('.edit-user-control > .edit-user-name').each(function () {
            a = $(this).children('a');
            input = $(this).children('input');
            a.text(input.val());
            a.removeClass('hidden');
            input.addClass('hidden');
        });
    } else {
        $('.edit-user-control > .edit-user-name').each(function () {
            $(this).children('a').addClass('hidden');
            $(this).children('input').removeClass('hidden');
        });
    }
}

users_list_table_options = {
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ active users",
        "infoEmpty": "Showing 0 to 0 of 0 entries",
        "infoFiltered": "",
        "emptyTable": "No data in table",
        "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "destroy": true,
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [ 2, 'asc'],
    "stateSave": true,
    "stateDuration": 0,
    "pagingType": "full_numbers",
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                $(td).html('<div class="edit-user-toggles">' + 
                    '<button class="btn btn-xs btn-warning delete-user" data-id="' + rowData['row_id'] + '" data-toggle="button"><i class="fa fa-trash-o fa-fw"></i> Delete</button>&nbsp' +
                    '<button class="btn btn-xs btn-warning purge-user" data-id="' + rowData['row_id'] + '" data-toggle="button"><i class="fa fa-eraser fa-fw"></i> Purge</button>&nbsp&nbsp&nbsp' +
                    '<input type="checkbox" id="keep_history-' + rowData['user_id'] + '" name="keep_history" value="1" ' + rowData['keep_history'] + '><label class="edit-tooltip" for="keep_history-' + rowData['user_id'] + '" data-toggle="tooltip" title="Toggle History"><i class="fa fa-history fa-lg fa-fw"></i></label>&nbsp' +
                    '<input type="checkbox" id="allow_guest-' + rowData['user_id'] + '" name="allow_guest" value="1" ' + rowData['allow_guest'] + '><label class="edit-tooltip" for="allow_guest-' + rowData['user_id'] + '" data-toggle="tooltip" title="Toggle Guest Access"><i class="fa fa-unlock-alt fa-lg fa-fw"></i></label>&nbsp' +
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
                var inactive = '';
                if (!rowData['is_active']) { inactive = '<span class="inactive-user-tooltip" data-toggle="tooltip" title="User not on Plex server"><i class="fa fa-exclamation-triangle"></i></span>'; }
                $(td).html('<a href="' + page('user', rowData['user_id']) + '"" title="' + rowData['username'] + '"><div class="users-poster-face" style="background-image: url(' + page('pms_image_proxy', cellData, null, 80, 80, null, null, null, 'user') + ');">' + inactive + '</div></a>');
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
                    $(td).html('<div class="edit-user-name" data-id="' + rowData['row_id'] + '">' +
                        '<a href="' + page('user', rowData['user_id']) + '" title="' + rowData['username'] + '">' + cellData + '</a>' +
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
            "className": "no-wrap"
        },
        {
            "targets": [4],
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
            "width": "10%",
            "className": "no-wrap modal-control-ip"
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
            "className": "no-wrap modal-control"
        },
        {
            "targets": [6],
            "data":"player",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var transcode_dec = '';
                    if (rowData['transcode_decision'] === 'transcode') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Transcode"><i class="fa fa-server fa-fw"></i></span>';
                    } else if (rowData['transcode_decision'] === 'copy') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Stream"><i class="fa fa-stream fa-fw"></i></span>';
                    } else if (rowData['transcode_decision'] === 'direct play') {
                        transcode_dec = '<span class="transcode-tooltip" data-toggle="tooltip" title="Direct Play"><i class="fa fa-play-circle fa-fw"></i></span>';
                    }
                    $(td).html('<div><a href="#" data-target="#info-modal" data-toggle="modal"><div style="float: left;">' + transcode_dec + '&nbsp;' + cellData + '</div></a></div>');
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "15%",
            "className": "no-wrap modal-control"
        },
        {
            "targets": [7],
            "data":"last_played",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
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
                    } else if (rowData['media_type']) {
                        $(td).html('<a href="' + page('info', rowData['rating_key']) + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "23%",
            "className": "datatable-wrap"
        },
        {
            "targets": [8],
            "data": "plays",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "searchable": false,
            "width": "7%",
            "className": "no-wrap"
        },
        {
            "targets": [9],
            "data": "duration",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(humanDuration(cellData, 'dhm', 's', false));
                }
            },
            "searchable": false,
            "width": "10%",
            "className": "no-wrap"
        }

    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        //$('html,body').scrollTop(0);
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
            container: 'body',
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
            toggleEditNames();
        }
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData) {
        if ($.inArray(rowData['user_id'], users_to_delete) !== -1) {
            $(row).find('button.delete-user[data-id="' + rowData['row_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
        if ($.inArray(rowData['user_id'], users_to_purge) !== -1) {
            $(row).find('button.purge-user[data-id="' + rowData['row_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
    }
}

$('#users_list_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
    var rowData = row.data();

    $.get('get_stream_data', {
        row_id: rowData['history_row_id'],
        user: rowData['friendly_name']
    }).then(function (jqXHR) {
        $("#info-modal").html(jqXHR);
    });
});

$('#users_list_table').on('click', 'td.modal-control-ip', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
    var rowData = row.data();

    $.get('get_ip_address_details', {
        ip_address: rowData['ip_address']
    }).then(function (jqXHR) {
        $("#ip-info-modal").html(jqXHR);
    });
});

$('#users_list_table').on('change', 'td.edit-control > .edit-user-toggles > input, td.edit-user-control > .edit-user-name > input', function () {
    var tr = $(this).parents('tr');
    var row = users_list_table.row(tr);
    var rowData = row.data();

    var keep_history = 0;
    var allow_guest = 0;
    if ($('#keep_history-' + rowData['user_id']).is(':checked')) {
        keep_history = 1;
    }
    if ($('#allow_guest-' + rowData['user_id']).is(':checked')) {
        allow_guest = 1;
    }

    friendly_name = tr.find('td.edit-user-control > .edit-user-name > input').val();

    $.ajax({
        url: 'edit_user',
        data: {
            user_id: rowData['user_id'],
            friendly_name: friendly_name,
            keep_history: keep_history,
            allow_guest: allow_guest,
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

    var index_delete = $.inArray(rowData['row_id'], users_to_delete);
    var index_purge = $.inArray(rowData['row_id'], users_to_purge);

    if (index_delete === -1) {
        users_to_delete.push(rowData['row_id']);
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

    var index_delete = $.inArray(rowData['row_id'], users_to_delete);
    var index_purge = $.inArray(rowData['row_id'], users_to_purge);

    if (index_purge === -1) {
        users_to_purge.push(rowData['row_id']);
    } else {
        users_to_purge.splice(index_purge, 1);
        if (index_delete != -1) {
            tr.find('button.delete-user').click();
        }
    }
    $(this).toggleClass('btn-warning').toggleClass('btn-danger');
});