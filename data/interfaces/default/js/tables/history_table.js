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
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ history items",
        "infoEmpty": "Showing 0 to 0 of 0 entries",
        "infoFiltered": "<span class='hidden-md hidden-sm hidden-xs'>(filtered from _MAX_ total entries)</span>",
        "emptyTable": "No data in table",
        "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "pagingType": "full_numbers",
    "stateSave": true,
    "stateDuration": 0,
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [ 1, 'desc'],
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['row_id'] === null) {
                    $(td).html('');
                } else {
                    $(td).html('<button class="btn btn-xs btn-warning" data-id="' + rowData['row_id'] + '"><i class="fa fa-trash-o fa-fw"></i> Delete</button>');
                }
            },
            "width": "5%",
            "className": "delete-control no-wrap hidden",
            "searchable": false,
            "orderable": false
        },
        {
            "targets": [1],
            "data": "date",
            "createdCell": function (td, cellData, rowData, row, col) {
                var date = moment(cellData, "X").format(date_format);
                if (rowData['state'] !== null) {
                    var state = '';
                    if (rowData['state'] === 'playing') {
                        state = '<span class="current-activity-tooltip" data-toggle="tooltip" title="Currently Playing"><i class="fa fa-fw fa-play"></i></span>';
                    } else if (rowData['state'] === 'paused') {
                        state = '<span class="current-activity-tooltip" data-toggle="tooltip" title="Currently Paused"><i class="fa fa-fw fa-pause"></i></span>';
                    } else if (rowData['state'] === 'buffering') {
                        state = '<span class="current-activity-tooltip" data-toggle="tooltip" title="Currently Buffering"><i class="fa fa-fw fa-spinner"></i></span>';
                    } else if (rowData['state'] === 'error') {
                        state = '<span class="current-activity-tooltip" data-toggle="tooltip" title="Playback Error"><i class="fa fa-fw fa-exclamation-triangle"></i></span>';
                    } else if (rowData['state'] === 'stopped') {
                        state = '<span class="current-activity-tooltip" data-toggle="tooltip" title="Currently Stopped"><i class="fa fa-fw fa-stop"></i></span>';
                    } else {
                        state = '<span class="current-activity-tooltip" data-toggle="tooltip" title="Unknown"><i class="fa fa-fw fa-question-circle"></i></span>';
                    }
                    $(td).html('<div><div style="float: left;">' + state + '&nbsp;' + date + '</div></div>');
                } else if (rowData['group_count'] > 1) {
                    expand_history = '<span class="expand-history-tooltip" data-toggle="tooltip" title="Show Detailed History"><i class="fa fa-plus-circle fa-fw"></i></span>';
                    $(td).html('<div><a href="#"><div style="float: left;">' + expand_history + '&nbsp;' + date + '</div></a></div>');
                } else {
                    $(td).html('<div style="float: left;"><i class="fa fa-plus-circle fa-fw fa-blank">&nbsp;</i>&nbsp;' + date + '</div>');
                }
            },
            "searchable": false,
            "width": "7%",
            "className": "no-wrap expand-history"
        },
        {
            "targets": [2],
            "data": "friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['user_id']) {
                        $(td).html('<a href="' + page('user', rowData['user_id']) + '" title="' + rowData['user'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="' + page('user', null, rowData['user']) + '" title="' + rowData['user'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
            "width": "9%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData) {
                    isPrivateIP(cellData).then(function () {
                        $(td).html(cellData || 'n/a');
                    }, function () {
                        external_ip = '<span class="external-ip-tooltip" data-toggle="tooltip" title="External IP"><i class="fa fa-map-marker fa-fw"></i></span>';
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal">'+ external_ip + cellData + '</a>');
                    });
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "8%",
            "className": "no-wrap modal-control-ip"
        },
        {
            "targets": [4],
            "data": "platform",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "product",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [6],
            "data": "player",
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
                    $(td).html('<div><a href="#" data-target="#info-modal" data-toggle="modal"><div style="float: left;">' + transcode_dec + '&nbsp;' + cellData + '</div></a></div>');
                }
            },
            "width": "10%",
            "className": "no-wrap modal-control"
        },
        {
            "targets": [7],
            "data": "full_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var icon = '';
                    var icon_title = '';
                    var parent_info = '';
                    var media_type = '';
                    var thumb_popover = '';
                    var fallback = (rowData['live']) ? 'poster-live' : 'poster';
                    var history = (rowData['state'] === null);
                    if (rowData['media_type'] === 'movie') {
                        icon = (rowData['live']) ? 'fa-broadcast-tower' : 'fa-film';
                        icon_title = (rowData['live']) ? 'Live TV' : 'Movie';
                        if (rowData['year']) { parent_info = ' (' + rowData['year'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="' + icon_title + '"><i class="fa ' + icon + ' fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, fallback) + '" data-height="120" data-width="80">' + cellData + parent_info + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key'], rowData['guid'], history, rowData['live']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'episode') {
                        icon = (rowData['live']) ? 'fa-broadcast-tower' : 'fa-television';
                        icon_title = (rowData['live']) ? 'Live TV' : 'Episode';
                        if (!isNaN(parseInt(rowData['parent_media_index'])) && !isNaN(parseInt(rowData['media_index']))) { parent_info = ' (' + short_season(rowData['parent_title']) + ' &middot; E' + rowData['media_index'] + ')'; }
                        else if (rowData['live'] && rowData['originally_available_at']) { parent_info = ' (' + rowData['originally_available_at'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="' + icon_title + '"><i class="fa ' + icon + ' fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, fallback) + '" data-height="120" data-width="80">' + cellData + parent_info + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key'], rowData['guid'], history, rowData['live']) + '"><div style="float: left;" >' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'track') {
                        if (rowData['parent_title']) { parent_info = ' (' + rowData['parent_title'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 300, null, null, null, 'cover') + '" data-height="80" data-width="80">' + cellData + parent_info + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key'], rowData['guid'], history, rowData['live']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'clip') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Clip"><i class="fa fa-video-camera fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, fallback) + '" data-height="120" data-width="80">' + cellData + parent_info + '</span>';
                        $(td).html('<div class="history-title"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></div>');
                    } else {
                        $(td).html('<a href="' + page('info', rowData['rating_key']) + '">' + cellData + '</a>');
                    }
                }
            },
            "width": "25%",
            "className": "datatable-wrap"
        },
        {
            "targets": [8],
            "data": "started",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null) {
                    $(td).html('n/a');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap"
        },
        {
            "targets": [9],
            "data": "paused_counter",
            "render": function (data, type, full) {
                if (data !== null) {
                    return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
                } else {
                    return '0 mins';
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap"
        },
        {
            "targets": [10],
            "data": "stopped",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null || (rowData['state'] != null && rowData['state'] != "stopped")) {
                    $(td).html('n/a');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap"
        },
        {
            "targets": [11],
            "data": "duration",
            "render": function (data, type, full) {
                if (data !== null) {
                    return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
                } else {
                    return data;
                }
            },
            "searchable": false,
            "width": "5%",
            "className": "no-wrap"
        },
        {
            "targets": [12],
            "data": "watched_status",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData == 1) {
                    $(td).html('<span class="watched-tooltip" data-toggle="tooltip" title="' + rowData['percent_complete'] + '%"><i class="fa fa-lg fa-circle"></i></span>');
                } else if (cellData == 0.5) {
                    $(td).html('<span class="watched-tooltip" data-toggle="tooltip" title="' + rowData['percent_complete'] + '%"><i class="fa fa-lg fa-adjust fa-rotate-180"></i></span>');
                } else {
                    $(td).html('<span class="watched-tooltip" data-toggle="tooltip" title="' + rowData['percent_complete'] + '%"><i class="fa fa-lg fa-circle-o"></i></span>');
                }
            },
            "searchable": false,
            "orderable": false,
            "className": "no-wrap",
            "width": "2%"
        },
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
            container: 'body',
            trigger: 'hover',
            placement: 'right',
            template: '<div class="popover history-thumbnail-popover" role="tooltip"><div class="arrow" style="top: 50%;"></div><div class="popover-content"></div></div>',
            content: function () {
                return '<div class="history-thumbnail" style="background-image: url(' + $(this).data('img') + '); height: ' + $(this).data('height') + 'px; width: ' + $(this).data('width') + 'px;" />';
            }
        });

        if ($('#row-edit-mode').hasClass('active')) {
            $('.history_table .delete-control').each(function () {
                $(this).removeClass('hidden');
            });
        }

        history_table.rows().every(function () {
            var rowData = this.data();
            if (rowData['group_count'] != 1 && rowData['reference_id'] in history_child_table) {
                // if grouped row and a child table was already created
                $(this.node()).find('i.fa.fa-plus-circle').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');
                this.child(childTableFormat(rowData)).show();
                createChildTable(this, rowData)
            }
        });

        $("#history_table_info").append('<span class="hidden-md hidden-sm hidden-xs"> with a duration of ' + settings.json.filter_duration +
            ' (filtered from ' + settings.json.total_duration + ' total)</span>');
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0);
        $('[data-toggle="tooltip"]').tooltip('destroy');
        $('[data-toggle="popover"]').popover('destroy');
    },
    "rowCallback": function (row, rowData, rowIndex) {
        if (rowData['group_count'] == 1) {
            // if no grouped rows simply toggle the delete button
            if ($.inArray(rowData['row_id'], history_to_delete) !== -1) {
                $(row).find('button[data-id="' + rowData['row_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
            }
        } else if (rowData['row_id'] !== null) {
            // if grouped rows
            // toggle the parent button to danger
            $(row).find('button[data-id="' + rowData['row_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
            // check if any child rows are not selected
            var group_ids = rowData['group_ids'].split(',').map(Number);
            group_ids.forEach(function (id) {
                var index = $.inArray(id, history_to_delete);
                if (index == -1) {
                    $(row).find('button[data-id="' + rowData['row_id'] + '"]').addClass('btn-warning').removeClass('btn-danger');
                }
            });
        }

        if (rowData['group_count'] != 1 && rowData['reference_id'] in history_child_table) {
            // if grouped row and a child table was already created
            $(row).addClass('shown')
            history_table.row(row).child(childTableFormat(rowData)).show();
        }

        if (rowData['state'] !== null) {
            $(row).addClass('current-activity-row');
        }
    }
};

// Parent table platform modal
$('.history_table').on('click', '> tbody > tr > td.modal-control', function () {
    var tr = $(this).closest('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    $.get('get_stream_data', {
        row_id: rowData['row_id'],
        session_key: rowData['session_key'],
        user: rowData['friendly_name']
    }).then(function (jqXHR) {
        $("#info-modal").html(jqXHR);
    });
});

// Parent table ip address modal
$('.history_table').on('click', '> tbody > tr > td.modal-control-ip', function () {
    var tr = $(this).closest('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    $.get('get_ip_address_details', {
        ip_address: rowData['ip_address']
    }).then(function (jqXHR) {
        $("#ip-info-modal").html(jqXHR);
    });
});

// Parent table delete mode
$('.history_table').on('click', '> tbody > tr > td.delete-control > button', function () {
    var tr = $(this).closest('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    if (rowData['group_count'] == 1) {
        // if no grouped rows simply add or remove row from history_to_delete
        var index = $.inArray(rowData['row_id'], history_to_delete);
        if (index === -1) {
            history_to_delete.push(rowData['row_id']);
        } else {
            history_to_delete.splice(index, 1);
        }
        $(this).toggleClass('btn-warning').toggleClass('btn-danger');
    } else {
        // if grouped rows
        if ($(this).hasClass('btn-warning')) {
            // add all grouped rows to history_to_delete
            var group_ids = rowData['group_ids'].split(',').map(Number);
            group_ids.forEach(function (id) {
                var index = $.inArray(id, history_to_delete);
                if (index == -1) {
                    history_to_delete.push(id);
                }
            });
            $(this).toggleClass('btn-warning').toggleClass('btn-danger');
            if (row.child.isShown()) {
                // if child table is visible, toggle all child buttons to danger
                tr.next().find('td.delete-control > button.btn-warning').toggleClass('btn-warning').toggleClass('btn-danger');
            }
        } else {
            // remove all grouped rows to history_to_delete
            var group_ids = rowData['group_ids'].split(',').map(Number);
            group_ids.forEach(function (id) {
                var index = $.inArray(id, history_to_delete);
                if (index != -1) {
                    history_to_delete.splice(index, 1);
                }
            });
            $(this).toggleClass('btn-warning').toggleClass('btn-danger');
            if (row.child.isShown()) {
                // if child table is visible, toggle all child buttons to warning
                tr.next().find('td.delete-control > button.btn-danger').toggleClass('btn-warning').toggleClass('btn-danger');
            }
        }
    }
});

// Parent table expand detailed history
$('.history_table').on('click', '> tbody > tr > td.expand-history a', function () {
    var tr = $(this).closest('tr');
    var row = history_table.row(tr);
    var rowData = row.data();
    
    $(this).find('i.fa').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');

    if (row.child.isShown()) {
        $('div.slider', row.child()).slideUp(function () {
            row.child.hide();
            tr.removeClass('shown');
            delete history_child_table[rowData['reference_id']];
        });
    } else {
        tr.addClass('shown');
        row.child(childTableFormat(rowData)).show();
        createChildTable(row, rowData);
    }
});


// Initialize the detailed history child table options using the parent table options
function childTableOptions(rowData) {
    history_child_options = history_table_options;
    // Remove settings that are not necessary
    history_child_options.searching = false;
    history_child_options.lengthChange = false;
    history_child_options.info = false;
    history_child_options.pageLength = 10;
    history_child_options.bStateSave = false;
    history_child_options.ajax = {
        url: 'get_history',
        type: 'post',
        data: function (d) {
            return {
                json_data: JSON.stringify(d),
                grouping: false,
                reference_id: rowData['reference_id']
            };
        }
    }
    history_child_options.fnDrawCallback = function (settings) {
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('.expand-history-tooltip').tooltip({ container: 'body' });
        $('.external-ip-tooltip').tooltip({ container: 'body' });
        $('.transcode-tooltip').tooltip({ container: 'body' });
        $('.media-type-tooltip').tooltip({ container: 'body' });
        $('.watched-tooltip').tooltip({ container: 'body' });
        $('.thumb-tooltip').popover({
            html: true,
            sanitize: false,
            container: 'body',
            trigger: 'hover',
            placement: 'right',
            template: '<div class="popover history-thumbnail-popover" role="tooltip"><div class="arrow" style="top: 50%;"></div><div class="popover-content"></div></div>',
            content: function () {
                return '<div class="history-thumbnail" style="background-image: url(' + $(this).data('img') + '); height: ' + $(this).data('height') + 'px;" />';
            }
        });

        if ($('#row-edit-mode').hasClass('active')) {
            $('.history_table .delete-control').each(function () {
                $(this).removeClass('hidden');
            });
        }

        $(this).closest('div.slider').slideDown();
    }

    return history_child_options;
}

// Format the detailed history child table
function childTableFormat(rowData) {
    return '<div class="slider">' +
            '<table id="history_child-' + rowData['reference_id'] + '" width="100%">' +
            '<thead>' +
            '<tr>' +
                '<th align="left" id="delete_row">Delete</th>' +
                '<th align="left" id="date">Date</th>' +
                '<th align="left" id="friendly_name">User</th>' +
                '<th align="left" id="ip_address">IP Address</th>' +
                '<th align="left" id="platform">Platform</th>' +
                '<th align="left" id="product">Product</th>' +
                '<th align="left" id="player">Player</th>' +
                '<th align="left" id="title">Title</th>' +
                '<th align="left" id="started">Started</th>' +
                '<th align="left" id="paused_counter">Paused</th>' +
                '<th align="left" id="stopped">Stopped</th>' +
                '<th align="left" id="duration">Duration</th>' +
                '<th align="left" id="percent_complete"></th>' +
            '</tr>' +
            '</thead>' +
            '<tbody>' +
            '</tbody>' +
            '</table>' +
            '</div>';
}

// Create the detailed history child table
history_child_table = {};
function createChildTable(row, rowData) {
    history_child_options = childTableOptions(rowData);
    // initialize the child table
    history_child_table[rowData['reference_id']] = $('#history_child-' + rowData['reference_id']).DataTable(history_child_options);

    // Set child table column visibility to match parent table
    var visibility = history_table.columns().visible();
    for (var i = 0; i < visibility.length; i++) {
        if (!(visibility[i])) { history_child_table[rowData['reference_id']].column(i).visible(visibility[i]); }
    }
    history_table.on('column-visibility', function (e, settings, colIdx, visibility) {
        if (row.child.isShown()) {
            history_child_table[rowData['reference_id']].column(colIdx).visible(visibility);
        }
    });

    // Child table platform modal
    $('#history_child-' + rowData['reference_id']).on('click', 'td.modal-control', function () {
        var tr = $(this).closest('tr');
        var childRow = history_child_table[rowData['reference_id']].row(tr);
        var childRowData = childRow.data();

        $.get('get_stream_data', {
            row_id: childRowData['row_id'],
            user: childRowData['friendly_name']
        }).then(function (jqXHR) {
            $("#info-modal").html(jqXHR);
        });
    });

    // Child table ip address modal
    $('#history_child-' + rowData['reference_id']).on('click', 'td.modal-control-ip', function () {
        var tr = $(this).closest('tr');
        var childRow = history_child_table[rowData['reference_id']].row(tr);
        var childRowData = childRow.data();

        $.get('get_ip_address_details', {
            ip_address: childRowData['ip_address']
        }).then(function (jqXHR) {
            $("#ip-info-modal").html(jqXHR);
        });
    });

    // Child table delete mode
    $('#history_child-' + rowData['reference_id']).on('click', 'td.delete-control > button', function () {
        var tr = $(this).closest('tr');
        var childRow = history_child_table[rowData['reference_id']].row(tr);
        var childRowData = childRow.data();

        // add or remove row from history_to_delete
        var index = $.inArray(childRowData['row_id'], history_to_delete);
        if (index === -1) {
            history_to_delete.push(childRowData['row_id']);
        } else {
            history_to_delete.splice(index, 1);
        }
        $(this).toggleClass('btn-warning').toggleClass('btn-danger');

        tr.parents('tr').prev().find('td.delete-control > button.btn-warning').toggleClass('btn-warning').toggleClass('btn-danger');
        // check if any child rows are not selected
        var group_ids = rowData['group_ids'].split(',').map(Number);
        group_ids.forEach(function (id) {
            var index = $.inArray(id, history_to_delete);
            if (index == -1) {
                // if any child row is not selected, toggle parent button to warning
                tr.parents('tr').prev().find('td.delete-control > button.btn-danger').addClass('btn-warning').removeClass('btn-danger');
            }
        });
    });
}

