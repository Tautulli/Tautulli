playlists_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ export items",
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
    "order": [0, 'asc'],
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": "title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var smart = '<i class="fa fa-blank fa-fw"></i>';
                    if (rowData['smart']) {
                        smart = '<span class="media-type-tooltip" data-toggle="tooltip" title="Smart Playlist"><i class="fa fa-cog fa-fw"></i></span>&nbsp;'
                    }
                    $(td).html('<a href="' + page('info', rowData['ratingKey']) + '&section_id=' + rowData['librarySectionID'] +'">' + smart + cellData + '</a>');
                }
            },
            "width": "60%",
            "className": "no-wrap"
        },
        {
            "targets": [1],
            "data": "leafCount",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    var type = MEDIA_TYPE_HEADERS[rowData['playlistType']] || '';
                    if (rowData['leafCount'] === 1) {
                        type = type.slice(0, -1);
                    }
                    $(td).html(cellData + ' ' + type);
                }
            },
            "width": "20%",
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "data": "duration",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(humanDuration(cellData, 'dhm'));
                }
            },
            "width": "20%",
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
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0);
        $('[data-toggle="tooltip"]').tooltip('destroy');
    },
    "rowCallback": function (row, rowData, rowIndex) {
    }
};