var date_format = 'YYYY-MM-DD hh:mm';
var time_format = 'hh:mm a';

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
    "responsive": {
        details: false
    },
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ history items",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"(filtered from _MAX_ total entries)",
        "emptyTable": "No data in table",
    },
    "stateSave": false,
    "sPaginationType": "bootstrap",
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [ 1, 'desc'],
    "columnDefs": [
        {
            "targets": [0],
            "data":"id",
            "visible": false,
            "searchable": false,
            "className": "no-wrap"
        },
        {
            "targets": [1],
            "data":"date",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['stopped'] === null) {
                    $(td).addClass('currentlyWatching');
                    $(td).html('Currently watching...');
                } else {
                    $(td).html(moment(cellData,"X").format(date_format));
                }
            },
            "searchable": false,
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "data":"friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="user?user=' + rowData['user'] + '">' + cellData + '</a>');
                } else {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data":"platform",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="#info-modal" data-toggle="modal"><span data-toggle="tooltip" data-placement="left" title="Stream Info" id="stream-info"><i class="fa fa-lg fa-info-circle"></i></span></a>&nbsp'+cellData);
                }
            },
            "className": "modal-control no-wrap"
        },
        {
            "targets": [4],
            "data":"ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if ((cellData == '') || (cellData == '0')) {
                    $(td).html('n/a');
                }
            },
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data":"title",
            "name":"title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['media_type'] === 'movie' || rowData['media_type'] === 'episode') {
                        $(td).html('<div><div style="float: left;"><a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a></div><div style="float: right; text-align: right; padding-right: 5px;"><i class="fa fa-video-camera"></i></div></div>');
                    } else if (rowData['media_type'] === 'track') {
                        $(td).html('<div><div style="float: left;">' + cellData + '</div><div style="float: right; text-align: right; padding-right: 5px;"><i class="fa fa-music"></i></div></div>');
                    } else {
                        $(td).html('<a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a>');
                    }
                }
            }
        },
        {
            "targets": [6],
            "data":"started",
            "render": function ( data, type, full ) {
                return moment(data, "X").format(time_format);
            },
            "searchable": false,
            "className": "no-wrap"
        },
        {
            "targets": [7],
            "data":"paused_counter",
            "render": function ( data, type, full ) {
                return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
            },
            "searchable": false,
            "className": "no-wrap"
        },
        {
            "targets": [8],
            "data":"stopped",
            "render": function ( data, type, full ) {
                if (data !== null) {
                    return moment(data, "X").format(time_format);
                } else {
                    return data;
                }
            },
            "searchable": false,
            "className": "no-wrap"
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
            "className": "no-wrap"
        },
        {
            "targets": [10],
            "data":"percent_complete",
            "render": function ( data, type, full ) {
                if (data < 85) {
                    return '<span class="badge">'+Math.round(data)+'%</span>';
                } else {
                    return '<span class="badge">100%</span>';
                }
            },
            "searchable": false,
            "className": "no-wrap"
        },
        {
            "targets": [11],
            "data":"grandparent_rating_key",
            "visible": false,
            "searchable": false
        },
        {
            "targets": [12],
            "data":"rating_key",
            "visible": false,
            "searchable": false
        },
        {
            "targets": [13],
            "data":"media_type",
            "searchable":false,
            "visible":false
        },
        {
            "targets": [14],
            "data":"user",
            "searchable":false,
            "visible":false
        }

    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').addClass('success').fadeOut();
    },
    "preDrawCallback": function(settings) {
        $('#ajaxMsg').html("<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>");
        $('#ajaxMsg').addClass('success').fadeIn();
    }
}

$('#history_table').on('mouseenter', 'td.modal-control span', function () {
    $(this).tooltip();
});

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