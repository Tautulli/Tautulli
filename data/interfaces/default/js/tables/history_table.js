var date_format = 'YYYY-MM-DD';
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
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ history items",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"(filtered from _MAX_ total entries)",
        "emptyTable": "No data in table",
    },
    "sPaginationType": "bootstrap",
    "stateSave": true,
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [ 0, 'desc'],
    "columnDefs": [
        {
            "targets": [0],
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
            "targets": [1],
            "data":"friendly_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['user_id'] !== '') {
                        $(td).html('<a href="user?user_id=' + rowData['user_id'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="user?user=' + rowData['user'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap hidden-phone"
        },
        {
            "targets": [2],
            "data":"player",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="#info-modal" data-toggle="modal"><span data-toggle="tooltip" data-placement="left" title="Stream Info" id="stream-info"><i class="fa fa-lg fa-info-circle"></i></span></a>&nbsp'+cellData);
                }
            },
            "className": "modal-control no-wrap hidden-tablet hidden-phone"
        },
        {
            "targets": [3],
            "data":"ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if ((cellData == '') || (cellData == '0')) {
                    $(td).html('n/a');
                }
            },
            "className": "no-wrap hidden-phone"
        },
        {
            "targets": [4],
            "data":"full_title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    if (rowData['media_type'] === 'movie' || rowData['media_type'] === 'episode') {
                        var transcode_dec = '';
                        if (rowData['video_decision'] === 'transcode') {
                            transcode_dec = '<i class="fa fa-server"></i>&nbsp';
                        }
                        $(td).html('<div><div style="float: left;"><a href="info?source=history&item_id=' + rowData['id'] + '">' + cellData + '</a></div><div style="float: right; text-align: right; padding-right: 5px;">' + transcode_dec + '<i class="fa fa-video-camera"></i></div></div>');
                    } else if (rowData['media_type'] === 'track') {
                        $(td).html('<div><div style="float: left;">' + cellData + '</div><div style="float: right; text-align: right; padding-right: 5px;"><i class="fa fa-music"></i></div></div>');
                    } else {
                        $(td).html('<a href="info?item_id=' + rowData['id'] + '">' + cellData + '</a>');
                    }
                }
            }
        },
        {
            "targets": [5],
            "data":"started",
            "render": function ( data, type, full ) {
                return moment(data, "X").format(time_format);
            },
            "searchable": false,
            "className": "no-wrap hidden-tablet hidden-phone"
        },
        {
            "targets": [6],
            "data":"paused_counter",
            "render": function ( data, type, full ) {
                if (data !== null) {
                    return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
                } else {
                    return '0 mins';
                }
            },
            "searchable": false,
            "className": "no-wrap hidden-phone"
        },
        {
            "targets": [7],
            "data":"stopped",
            "render": function ( data, type, full ) {
                if (data !== null) {
                    return moment(data, "X").format(time_format);
                } else {
                    return data;
                }
            },
            "searchable": false,
            "className": "no-wrap hidden-tablet hidden-phone"
        },
        {
            "targets": [8],
            "data":"duration",
            "render": function ( data, type, full ) {
                if (data !== null) {
                    return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
                } else {
                    return data;
                }
            },
            "searchable": false,
            "className": "no-wrap hidden-phone"
        },
        {
            "targets": [9],
            "data":"percent_complete",
            "render": function ( data, type, full ) {
                if (data > 80) {
                    return '<i class="fa fa-lg fa-circle"></i>'
                } else if (data > 40) {
                    return '<i class="fa fa-lg fa-adjust fa-rotate-180"></i>'
                } else {
                    return '<i class="fa fa-lg fa-circle-o"></i>'
                }
            },
            "searchable": false,
            "orderable": true,
            "className": "no-wrap hidden-tablet hidden-phone"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();
    },
    "preDrawCallback": function(settings) {
        var msg = "<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>";
        showMsg(msg, false, false, 0)
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