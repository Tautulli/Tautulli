playlists_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ playlists",
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
                    var breadcrumb = '';
                    if (rowData['userID']) {
                        breadcrumb = '&user_id=' + rowData['userID'];
                    } else if (rowData['librarySectionID']) {
                        breadcrumb = '&section_id=' + rowData['librarySectionID'];
                    }
                    var thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['composite'], rowData['ratingKey'], 300, 300, null, null, null, 'cover') + '" data-height="80" data-width="80">' + cellData + '</span>';
                    $(td).html(smart + '<a href="' + page('info', rowData['ratingKey']) + breadcrumb +'">' + thumb_popover + '</a>');
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
    },
    "preDrawCallback": function(settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0);
        $('[data-toggle="tooltip"]').tooltip('destroy');
    },
    "rowCallback": function (row, rowData, rowIndex) {
    }
};