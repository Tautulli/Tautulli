var libraries_to_purge = [];

libraries_list_table_options = {
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ active libraries",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"",
        "emptyTable": "No data in table",
    },
    "destroy": true,
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "order": [ 1, 'asc'],
    "autoWidth": true,
    "stateSave": true,
    "pagingType": "bootstrap",
    "columnDefs": [
        {
            "targets": [0],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                $(td).html('<div class="edit-library-toggles">' +
                    '<button class="btn btn-xs btn-warning purge-library" data-id="' + rowData['section_id'] + '" data-toggle="button"><i class="fa fa-eraser fa-fw"></i> Purge</button>&nbsp&nbsp&nbsp' +
                    '<input type="checkbox" id="do_notify-' + rowData['section_id'] + '" name="do_notify" value="1" ' + rowData['do_notify'] + '><label class="edit-tooltip" for="do_notify-' + rowData['section_id'] + '" data-toggle="tooltip" title="Toggle Notifications"><i class="fa fa-bell fa-lg fa-fw"></i></label>&nbsp' +
                    '<input type="checkbox" id="keep_history-' + rowData['section_id'] + '" name="keep_history" value="1" ' + rowData['keep_history'] + '><label class="edit-tooltip" for="keep_history-' + rowData['section_id'] + '" data-toggle="tooltip" title="Toggle History"><i class="fa fa-history fa-lg fa-fw"></i></label>&nbsp');
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
                if (cellData === '') {
                    $(td).html('<a href="library?section_id=' + rowData['section_id'] + '"><div class="libraries-poster-face" style="background-image: url(interfaces/default/images/gravatar-default-80x80.png);"></div></a>');
                } else {
                    $(td).html('<a href="library?section_id=' + rowData['section_id'] + '"><div class="libraries-poster-face" style="background-image: url(pms_image_proxy?img=' + rowData['library_thumb'] + '&width=80&height=80&fallback=poster);"></div></a>');
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
                if (cellData !== '') {
                    $(td).html('<div data-id="' + rowData['section_id'] + '"><a href="library?section_id=' + rowData['section_id'] + '">' + cellData + '</a></div>');
                } else {
                    $(td).html(cellData);
                }
            },
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "section_type",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "10%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [4],
            "data": "count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null) {
                    $(td).html(cellData);
                } else {
                    $(td).html('n/a');
                }

            },
            "width": "10%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [5],
            "data": "parent_count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null) {
                    $(td).html(cellData);
                } else {
                    $(td).html('n/a');
                }

            },
            "width": "10%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [6],
            "data": "child_count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null) {
                    $(td).html(cellData);
                } else {
                    $(td).html('n/a');
                }

            },
            "width": "10%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [7],
            "data": "last_accessed",
            "render": function (data, type, full) {
                if (data) {
                    return moment(data, "X").fromNow();
                } else {
                    return "never";
                }
            },
            "searchable": false,
            "width": "10%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [8],
            "data":"last_watched",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var media_type = '';
                    var thumb_popover = ''
                    if (rowData['media_type'] === 'movie') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Movie"><i class="fa fa-film fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=80&height=120&fallback=poster" data-height="120">' + cellData + '</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;">' + media_type + '&nbsp' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'episode') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Episode"><i class="fa fa-television fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=80&height=120&fallback=poster" data-height="120">' + cellData + '</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;" >' + media_type + '&nbsp' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'track') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="pms_image_proxy?img=' + rowData['thumb'] + '&width=80&height=80&fallback=poster" data-height="80">' + cellData + '</span>'
                        $(td).html('<div class="history-title"><a href="info?source=history&rating_key=' + rowData['rating_key'] + '"><div style="float: left;">' + media_type + '&nbsp' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type']) {
                        $(td).html('<a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('n/a');
                    }
                }
            },
            "width": "25%",
            "className": "hidden-sm hidden-xs"
        },
        {
            "targets": [9],
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
        $('.thumb-tooltip').popover({
            html: true,
            trigger: 'hover',
            placement: 'right',
            content: function () {
                return '<div style="background-image: url(' + $(this).data('img') + '); width: 80px; height: ' + $(this).data('height') + 'px;" />';
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
        if ($.inArray(rowData['section_id'], libraries_to_purge) !== -1) {
            $(row).find('button[data-id="' + rowData['section_id'] + '"]').toggleClass('btn-warning').toggleClass('btn-danger');
        }
    }
}

$('#libraries_list_table').on('change', 'td.edit-control > .edit-library-toggles > input', function () {
    var tr = $(this).parents('tr');
    var row = libraries_list_table.row(tr);
    var rowData = row.data();

    var do_notify = 0;
    var keep_history = 0;
    if ($('#do_notify-' + rowData['section_id']).is(':checked')) {
        do_notify = 1;
    }
    if ($('#keep_history-' + rowData['section_id']).is(':checked')) {
        keep_history = 1;
    }
    
    $.ajax({
        url: 'edit_library',
        data: {
            section_id: rowData['section_id'],
            do_notify: do_notify,
            keep_history: keep_history,
            custom_thumb: rowData['library_thumb']
        },
        cache: false,
        async: true,
        success: function (data) {
            var msg = "Library updated";
            showMsg(msg, false, true, 2000);
        }
    });
});

$('#libraries_list_table').on('click', 'td.edit-control > .edit-library-toggles > button.purge-library', function () {
    var tr = $(this).parents('tr');
    var row = libraries_list_table.row(tr);
    var rowData = row.data();

    var index_purge = $.inArray(rowData['section_id'], libraries_to_purge);

    if (index_purge === -1) {
        libraries_to_purge.push(rowData['section_id']);
    } else {
        libraries_to_purge.splice(index_purge, 1);
    }
    $(this).toggleClass('btn-warning').toggleClass('btn-danger');
});