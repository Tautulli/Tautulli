var date_format = 'YYYY-MM-DD';
var time_format = 'hh:mm a';

$.ajax({
    url: 'get_date_formats',
    type: 'GET',
    success: function (data) {
        date_format = data.date_format;
        time_format = data.time_format;
    }
});

var refresh_child_tables = false;

media_info_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ library items",
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
    "order": [1, 'asc'],
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": "added_at",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData) {
                    var expand_details = '';
                    var date = '';
                    if (cellData !== null && cellData !== '') {
                        date = moment(cellData, "X").format(date_format);
                    }
                    if (rowData['media_type'] === 'show') {
                        expand_details = '<span class="expand-media-info-tooltip" data-toggle="tooltip" title="Show Seasons"><i class="fa fa-plus-circle fa-fw"></i></span>';
                        $(td).html('<div><a href="#"><div style="float: left;">' + expand_details + '&nbsp;' + date + '</div></a></div>');
                    } else if (rowData['media_type'] === 'season') {
                        expand_details = '<span class="expand-media-info-tooltip" data-toggle="tooltip" title="Show Episodes"><i class="fa fa-plus-circle fa-fw"></i></span>';
                        $(td).html('<div><a href="#"><div style="float: left;">' + expand_details + '&nbsp;' + date + '</div></a></div>');
                    } else if (rowData['media_type'] === 'artist') {
                        expand_details = '<span class="expand-media-info-tooltip" data-toggle="tooltip" title="Show Albums"><i class="fa fa-plus-circle fa-fw"></i></span>';
                        $(td).html('<div><a href="#"><div style="float: left;">' + expand_details + '&nbsp;' + date + '</div></a></div>');
                    } else if (rowData['media_type'] === 'album') {
                        expand_details = '<span class="expand-media-info-tooltip" data-toggle="tooltip" title="Show Tracks"><i class="fa fa-plus-circle fa-fw"></i></span>';
                        $(td).html('<div><a href="#"><div style="float: left;">' + expand_details + '&nbsp;' + date + '</div></a></div>');
                    } else if (rowData['media_type'] === 'photo_album') {
                        expand_details = '<span class="expand-media-info-tooltip" data-toggle="tooltip" title="Show Photos"><i class="fa fa-plus-circle fa-fw"></i></span>';
                        $(td).html('<div><a href="#"><div style="float: left;">' + expand_details + '&nbsp;' + date + '</div></a></div>');
                    } else {
                        $(td).html('<div style="float: left;"><i class="fa fa-plus-circle fa-fw fa-blank"></i>&nbsp;' + date + '</div>');
                    }
                }
            },
            "width": "7%",
            "className": "no-wrap expand-media-info",
            "searchable": false
        },
        {
            "targets": [1],
            "data": "sort_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var parent_info = '';
                    var media_type = '';
                    var thumb_popover = '';
                    if (rowData['media_type'] === 'movie') {
                        if (rowData['year']) { parent_info = ' (' + rowData['year'] + ')'; }
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Movie"><i class="fa fa-film fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, 'poster') + '" data-height="120" data-width="80">' + rowData['title'] + parent_info + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'show') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="TV Show"><i class="fa fa-television fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, 'poster') + '" data-height="120" data-width="80">' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'season') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Season"><i class="fa fa-television fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, 'poster') + '" data-height="120" data-width="80">' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left; padding-left: 15px;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'episode') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Episode"><i class="fa fa-television fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 500, 280, null, null, null, 'art') + '" data-height="80" data-width="140">E' + rowData['media_index'] + ' - ' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left; padding-left: 30px;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'artist') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Artist"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 300, null, null, null, 'cover') + '" data-height="80" data-width="80">' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'album') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Album"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 300, null, null, null, 'cover') + '" data-height="80" data-width="80">' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left; padding-left: 15px;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'track') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Track"><i class="fa fa-music fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 300, null, null, null, 'cover') + '" data-height="80" data-width="80">T' + rowData['media_index'] + ' - ' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left; padding-left: 30px;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'photo_album') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Photo Album"><i class="fa fa-camera fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, 'poster') + '" data-height="120" data-width="80">' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'photo') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Photo"><i class="fa fa-picture-o fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 300, 450, null, null, null, 'poster') + '" data-height="120" data-width="80">' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left; padding-left: 15px;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else if (rowData['media_type'] === 'clip') {
                        media_type = '<span class="media-type-tooltip" data-toggle="tooltip" title="Video"><i class="fa fa-video-camera fa-fw"></i></span>';
                        thumb_popover = '<span class="thumb-tooltip" data-toggle="popover" data-img="' + page('pms_image_proxy', rowData['thumb'], rowData['rating_key'], 500, 280, null, null, null, 'art') + '" data-height="80" data-width="140">' + rowData['title'] + '</span>';
                        $(td).html('<div class="history-title"><a href="' + page('info', rowData['rating_key']) + '"><div style="float: left; padding-left: 15px;">' + media_type + '&nbsp;' + thumb_popover + '</div></a></div>');
                    } else {
                        $(td).html(cellData);
                    }
                }
            },
            "width": "20%",
            "className": "no-wrap",
        },
        {
            "targets": [2],
            "data": "container",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "6%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "bitrate",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData + ' kbps');
                }
            },
            "width": "6%",
            "className": "no-wrap",
            "searchable": false
        },
        {
            "targets": [4],
            "data": "video_codec",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "8%",
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "video_resolution",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "8%",
            "className": "no-wrap"
        },
        {
            "targets": [6],
            "data": "video_framerate",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "8%",
            "className": "no-wrap"
        },
        {
            "targets": [7],
            "data": "audio_codec",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "8%",
            "className": "no-wrap"
        },
        {
            "targets": [8],
            "data": "audio_channels",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData + ' ch');
                }
            },
            "width": "8%",
            "className": "no-wrap"
        },
        {
            "targets": [9],
            "data": "file_size",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(humanFileSize(cellData));
                } else {
                    if (rowData['section_type'] != 'photo' && get_file_sizes != null) {
                        get_file_sizes = true;
                    }
                }
            },
            "width": "7%",
            "className": "no-wrap",
            "searchable": false
        },
        {
            "targets": [10],
            "data": "last_played",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    date = moment(cellData, "X").format(date_format);
                    $(td).html(date);
                }
            },
            "width": "7%",
            "className": "no-wrap",
            "searchable": false
        },
        {
            "targets": [11],
            "data": "play_count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "width": "5%",
            "className": "no-wrap",
            "searchable": false
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
            container: 'body',
            trigger: 'hover',
            placement: 'right',
            template: '<div class="popover history-thumbnail-popover" role="tooltip"><div class="arrow" style="top: 50%;"></div><div class="popover-content"></div></div>',
            content: function () {
                return '<div class="history-thumbnail" style="background-image: url(' + $(this).data('img') + '); height: ' + $(this).data('height') + 'px; width: ' + $(this).data('width') + 'px;" />';
            }
        });

        media_info_table.rows().every(function () {
            var rowData = this.data();
            if (rowData['rating_key'] in media_info_child_table) {
                // if a child table was already created
                $(this.node()).find('i.fa.fa-plus-circle').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');
                this.child(childTableFormatMedia(rowData)).show();
                createChildTableMedia(this, rowData)
            }
        });

        if (get_file_sizes) {
            $('#get_file_sizes_message').show();
            $('#refresh-media-info-table').prop('disabled', true);
            $.ajax({
                url: 'get_media_info_file_sizes',
                async: true,
                data: { section_id: section_id },
                complete: function (xhr, status) {
                    response = JSON.parse(xhr.responseText)
                    if (response.success == true) {
                        $('#get_file_sizes_message').hide();
                        $('#refresh-media-info-table').prop('disabled', false);
                        media_info_table.draw();
                    }
                }
            });
            get_file_sizes = false;
        }

        $("#media_info_table-SID-" + section_id + "_info").append('<span class="hidden-md hidden-sm hidden-xs"> with a total file size of ' +
            humanFileSize(settings.json.filtered_file_size) +
            ' (filtered from ' + humanFileSize(settings.json.total_file_size) + ')</span>');
    },
    "preDrawCallback": function (settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
    },
    "rowCallback": function (row, rowData, rowIndex) {
        if (rowData['rating_key'] in media_info_child_table) {
            // if a child table was already created
            $(row).addClass('shown')
            media_info_table.row(row).child(childTableFormatMedia(rowData)).show();
        }
    }
}

// Parent table expand detailed media info
$('.media_info_table').on('click', '> tbody > tr > td.expand-media-info a', function () {
    var tr = $(this).closest('tr');
    var row = media_info_table.row(tr);
    var rowData = row.data();

    $(this).find('i.fa').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');

    if (row.child.isShown()) {
        $('div.slider', row.child()).slideUp(function () {
            row.child.hide();
            tr.removeClass('shown');
            delete media_info_child_table[rowData['rating_key']];
        });
    } else {
        tr.addClass('shown');
        row.child(childTableFormatMedia(rowData)).show();
        createChildTableMedia(row, rowData);
    }
});

// Initialize the detailed media info child table options using the parent table options
function childTableOptionsMedia(rowData) {
    switch (rowData['media_type']) {
        case 'show':
            section_type = 'season';
            break;
        case 'season':
            section_type = 'episode';
            break;
        case 'artist':
            section_type = 'album';
            break;
        case 'album':
            section_type = 'track';
            break;
        case 'photo_album':
            section_type = 'picture';
            break;
    }

    media_info_table_options = media_info_table_options;
    // Remove settings that are not necessary
    media_info_table_options.searching = false;
    media_info_table_options.lengthChange = false;
    media_info_table_options.info = false;
    media_info_table_options.pageLength = 10;
    media_info_table_options.bStateSave = false;
    media_info_table_options.ajax = {
        url: 'get_library_media_info',
        type: 'post',
        data: function (d) {
            return {
                json_data: JSON.stringify(d),
                section_id: rowData['section_id'],
                section_type: section_type,
                rating_key: rowData['rating_key'],
                refresh: refresh_child_tables
            };
        }
    }
    media_info_table_options.fnDrawCallback = function (settings) {
        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('.expand-media-info-tooltip').tooltip({ container: 'body' });
        $('.media-type-tooltip').tooltip();
        $('.thumb-tooltip').popover({
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

        if (rowData['rating_key'] in media_info_child_table) {
            media_info_child_table[rowData['rating_key']].rows().every(function () {
                var childrowData = this.data();
                if (childrowData['rating_key'] in media_info_child_table) {
                    // if a child table was already created
                    $(this.node()).find('i.fa.fa-plus-circle').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');
                    this.child(childTableFormatMedia(childrowData)).show();
                    createChildTableMedia(this, childrowData)
                }
            });
        }

        if (get_file_sizes) {
            $('#refresh-media-info-table').prop('disabled', true);
            $.ajax({
                url: 'get_media_info_file_sizes',
                async: true,
                data: {
                    section_id: section_id,
                    rating_key: rowData['rating_key']
                },
                complete: function (xhr, status) {
                    response = JSON.parse(xhr.responseText)
                    if (response.success == true) {
                        $('#refresh-media-info-table').prop('disabled', false);
                        media_info_child_table[rowData['rating_key']].draw();
                    }
                }
            });
            get_file_sizes = false;
        }

        $(this).closest('div.slider').slideDown();
    }
    media_info_table_options.fnRowCallback = function (row, rowData, rowIndex) {
        if (rowData['rating_key'] in media_info_child_table) {
            // if a child table was already created
            $(row).addClass('shown')
            media_info_table.row(row).child(childTableFormatMedia(rowData)).show();
        }
    }

    return media_info_table_options;
}

// Format the detailed media info child table
function childTableFormatMedia(rowData) {
    return '<div class="slider">' +
            '<table id="media_info_child-' + rowData['rating_key'] + '" data-id="' + rowData['rating_key'] + '" width="100%">' +
            '<thead>' +
            '<tr>' +
                '<th align="left" id="added_at">Added At</th>' +
                '<th align="left" id="title">Title</th>' +
                '<th align="left" id="container">Container</th>' +
                '<th align="left" id="bitrate">Bitrate</th>' +
                '<th align="left" id="video_codec">Video Codec</th>' +
                '<th align="left" id="video_resolution">Video Resolution</th>' +
                '<th align="left" id="video_resolution">Video Framerate</th>' +
                '<th align="left" id="audio_codec">Audio Codec</th>' +
                '<th align="left" id="audio_channels">Audio Channels</th>' +
                '<th align="left" id="file_size">File Size</th>' +
                '<th align="left" id="last_played">Last Played</th>' +
                '<th align="left" id="total_plays">Total Plays</th>' +
            '</tr>' +
            '</thead>' +
            '<tbody>' +
            '</tbody>' +
            '</table>' +
            '</div>';
}

// Create the detailed media info child table
media_info_child_table = {};
function createChildTableMedia(row, rowData) {
    media_info_table_options = childTableOptionsMedia(rowData);
    // initialize the child table
    media_info_child_table[rowData['rating_key']] = $('#media_info_child-' + rowData['rating_key']).DataTable(media_info_table_options);

    // Set child table column visibility to match parent table
    var visibility = media_info_table.columns().visible();
    for (var i = 0; i < visibility.length; i++) {
        if (!(visibility[i])) { media_info_child_table[rowData['rating_key']].column(i).visible(visibility[i]); }
    }
    media_info_table.on('column-visibility', function (e, settings, colIdx, visibility) {
        if (row.child.isShown()) {
            media_info_child_table[rowData['rating_key']].column(colIdx).visible(visibility);
        }
    });

    // Child table expand detailed media info
    $('table[id^=media_info_child-' + rowData['rating_key'] + ']').on('click', '> tbody > tr > td.expand-media-info a', function () {
        var table_id = $(this).closest('table').data('id');
        var tr = $(this).closest('tr');
        var row = media_info_child_table[table_id].row(tr);
        var rowData = row.data();

        $(this).find('i.fa').toggleClass('fa-plus-circle').toggleClass('fa-minus-circle');

        if (row.child.isShown()) {
            $('div.slider', row.child()).slideUp(function () {
                row.child.hide();
                tr.removeClass('shown');
                delete media_info_child_table[rowData['rating_key']];
            });
        } else {
            tr.addClass('shown');
            row.child(childTableFormatMedia(rowData)).show();
            createChildTableMedia(row, rowData);
        }
    });
}