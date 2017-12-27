var libraries_to_delete = [];
var libraries_to_purge = [];

libraries_list_table_options = {
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ active libraries",
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
    "pagingType": "full_numbers",
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                $(td).html('<div class="edit-library-toggles">' +
                    '<button class="btn btn-xs btn-warning delete-library" data-id="' + rowData['section_id'] + '" data-toggle="button"><i class="fa fa-trash-o fa-fw"></i> Delete</button>&nbsp' +
                    '<button class="btn btn-xs btn-warning purge-library" data-id="' + rowData['section_id'] + '" data-toggle="button"><i class="fa fa-eraser fa-fw"></i> Purge</button>&nbsp&nbsp&nbsp' +
                    '<input type="checkbox" id="do_notify-' + rowData['section_id'] + '" name="do_notify" value="1" ' + rowData['do_notify'] + '><label class="edit-tooltip" for="do_notify-' + rowData['section_id'] + '" data-toggle="tooltip" title="Toggle Notifications"><i class="fa fa-bell fa-lg fa-fw"></i></label>&nbsp' +
                    '<input type="checkbox" id="keep_history-' + rowData['section_id'] + '" name="keep_history" value="1" ' + rowData['keep_history'] + '><label class="edit-tooltip" for="keep_history-' + rowData['section_id'] + '" data-toggle="tooltip" title="Toggle History"><i class="fa fa-history fa-lg fa-fw"></i></label>&nbsp' +
                    '<input type="checkbox" id="do_notify_created-' + rowData['section_id'] + '" name="do_notify_created" value="1" ' + rowData['do_notify_created'] + '><label class="edit-tooltip" for="do_notify_created-' + rowData['section_id'] + '" data-toggle="tooltip" title="Toggle Recently Added"><i class="fa fa-download fa-lg fa-fw"></i></label>&nbsp' +
                    '</div>');
            },
            "width": "7%",
            "className": "edit-control no-wrap hidden",
            "searchable": false,
            "orderable": false
        },
        {
            "targets": [1],
            "data": "library_thumb",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    if (rowData['library_thumb'].substring(0, 4) == "http") {
                        $(td).html('<a href="library?section_id=' + rowData['section_id'] + '"><div class="libraries-poster-face" style="background-image: url(' + rowData['library_thumb'] + ');"></div></a>');
                    } else {
                        $(td).html('<a href="library?section_id=' + rowData['section_id'] + '"><div class="libraries-poster-face svg-icon library-' + rowData['section_type'] + '"></div></a>');
                    }
                } else {
                    $(td).html('<a href="library?section_id=' + rowData['section_id'] + '"><div class="libraries-poster-face" style="background-image: url(../../images/cover.png);"></div></a>');
                }
            },
            "orderable": false,
            "searchable": false,
            "width": "5%",
            "className": "libraries-thumbs"
        },
        {
            "targets": [2],
            "data": "section_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html('<div data-id="' + rowData['section_id'] + '">' +
                        '<a href="library?section_id=' + rowData['section_id'] + '">' + cellData + '</a>' +
                        '</div>');
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "section_type",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(capitalizeFirstLetter(cellData));
                }
            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [4],
            "data": "count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }

            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "parent_count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }

            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [6],
            "data": "child_count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }

            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [7],
            "data": "last_accessed",
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
            "targets": [8],
            "data":"last_played",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var parent_info = '';
                    var media_type = '';
                    var thumb_popover = '';
                    if (rowData['media_type'] === 'movie') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Movie"><i class="fa fa-film fa-fw"></i></span>';
                        if (rowData['rating_key']) {
                            if (rowData['year']) { parent_info = ' (' + rowData['year'] + ')'; }
                            thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=450&fallback=poster" data-height="120" data-width="80">' + cellData + parent_info + '</span>'
                            $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                        } else {
                            thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="images/poster.png" data-height="120" data-width="80">' + cellData + parent_info + '</span>'
                            $(td).html('<div class="history-title"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></div>');
                        }
                    } else if (rowData['media_type'] === 'episode') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Episode"><i class="fa fa-television fa-fw"></i></span>';
                        if (rowData['rating_key']) {
                            if (rowData['parent_media_index'] && rowData['media_index']) { parent_info = ' (S' + rowData['parent_media_index'] + '&middot; E' + rowData['media_index'] + ')'; }
                            thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=450&fallback=poster" data-height="120" data-width="80">' + cellData + parent_info + '</span>'
                            $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;" >' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                        } else {
                            thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="images/poster.png" data-height="120" data-width="80">' + cellData + parent_info + '</span>'
                            $(td).html('<div class="history-title"><div style="float: left;" >' + media_type + '&nbsp;' + thumb_popover + '</div></div>');
                        }
                    } else if (rowData['media_type'] === 'track') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        if (rowData['rating_key']) {
                            if (rowData['parent_title']) { parent_info = ' (' + rowData['parent_title'] + ')'; }
                            thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=300&height=300&fallback=cover" data-height="80" data-width="80">' + cellData + parent_info + '</span>'
                            $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                        } else {
                            thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="images/cover.png" data-height="80" data-width="80">' + cellData + parent_info + '</span>'
                            $(td).html('<div class="history-title"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></div>');
                        }
                    } else if (rowData['media_type']) {
                        if (rowData['rating_key']) {
                            $(td).html('<a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a>');
                        } else {
                            $(td).html(cellData);
                        }
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "18%",
            "className": "datatable-wrap"
        },
        {
            "targets": [9],
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
            "targets": [10],
            "data": "duration",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(humanTimeClean(cellData));
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
        }
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData) {
        if ($.inArray(rowData['section_id'], libraries_to_delete) !== -1) {
            $(row).find('button.delete-library[data-id="' + rowData['section_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
        if ($.inArray(rowData['section_id'], libraries_to_purge) !== -1) {
            $(row).find('button.purge-library[data-id="' + rowData['section_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
    }
}

$('#libraries_list_table').on('change', 'td.edit-control > .edit-library-toggles > input', function () {
    var tr = $(this).parents('tr');
    var row = libraries_list_table.row(tr);
    var rowData = row.data();

    var do_notify = 0;
    var do_notify_created = 0;
    var keep_history = 0;
    if ($('#do_notify-' + rowData['section_id']).is(':checked')) {
        do_notify = 1;
    }
    if ($('#do_notify_created-' + rowData['section_id']).is(':checked')) {
        do_notify_created = 1;
    }
    if ($('#keep_history-' + rowData['section_id']).is(':checked')) {
        keep_history = 1;
    }
    if (rowData['custom_thumb']) {
        custom_thumb = rowData['custom_thumb']
    } else {
        custom_thumb = rowData['library_thumb']
    }
    
    $.ajax({
        url: 'edit_library',
        data: {
            section_id: rowData['section_id'],
            do_notify: do_notify,
            do_notify_created: do_notify_created,
            keep_history: keep_history,
            custom_thumb: custom_thumb
        },
        cache: false,
        async: true,
        success: function (data) {
            var msg = "Library updated";
            showMsg(msg, false, true, 2000);
        }
    });
});

$('#libraries_list_table').on('click', 'td.edit-control > .edit-library-toggles > button.delete-library', function () {
    var tr = $(this).parents('tr');
    var row = libraries_list_table.row(tr);
    var rowData = row.data();

    var index_delete = $.inArray(rowData['section_id'], libraries_to_delete);
    var index_purge = $.inArray(rowData['section_id'], libraries_to_purge);

    if (index_delete === -1) {
        libraries_to_delete.push(rowData['section_id']);
        if (index_purge === -1) {
            tr.find('button.purge-library').click();
        }
    } else {
        libraries_to_delete.splice(index_delete, 1);
        if (index_purge != -1) {
            tr.find('button.purge-library').click();
        }
    }
    $(this).toggleClass('btn-warning').toggleClass('btn-danger');

});

$('#libraries_list_table').on('click', 'td.edit-control > .edit-library-toggles > button.purge-library', function () {
    var tr = $(this).parents('tr');
    var row = libraries_list_table.row(tr);
    var rowData = row.data();

    var index_delete = $.inArray(rowData['section_id'], libraries_to_delete);
    var index_purge = $.inArray(rowData['section_id'], libraries_to_purge);

    if (index_purge === -1) {
        libraries_to_purge.push(rowData['section_id']);
    } else {
        libraries_to_purge.splice(index_purge, 1);
        if (index_delete != -1) {
            tr.find('button.delete-library').click();
        }
    }
    $(this).toggleClass('btn-warning').toggleClass('btn-danger');
});