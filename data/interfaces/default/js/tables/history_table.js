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
    "stateSave": false,
    "sPaginationType": "bootstrap",
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "order": [ 1, 'desc'],
    "columnDefs": [
        {
            "targets": [0],
            "data":"id",
            "visible": false,
            "searchable": false
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
            "searchable": false
        },
        {
            "targets": [2],
            "data":"user",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="user?user=' + cellData + '">' + cellData + '</a>');
                } else {
                    $(td).html(cellData);
                }
            },
        },
        {
            "targets": [3],
            "data":"platform",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="#info-modal" data-toggle="modal"><span data-toggle="tooltip" data-placement="left" title="Stream Info" id="stream-info" class="badge badge-inverse"><i class="fa fa-info"></i></span></a>&nbsp'+cellData);
                }
            },
            "className": "modal-control"
        },
        {
            "targets": [4],
            "data":"ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if ((cellData == '') || (cellData == '0')) {
                    $(td).html('n/a');
                }
            }
        },
        {
            "targets": [5],
            "data":"title",
            "name":"title",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="info?rating_key=' + rowData['rating_key'] + '">' + cellData + '</a>');
                }
            }
        },
        {
            "targets": [6],
            "data":"started",
            "render": function ( data, type, full ) {
                return moment(data, "X").format(time_format);
            },
            "searchable": false
        },
        {
            "targets": [7],
            "data":"paused_counter",
            "render": function ( data, type, full ) {
                return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
            },
            "searchable": false
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
            "searchable": false
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
            "searchable": false
        },
        {
            "targets": [10],
            "data":"percent_complete",
            "orderable": false,
            "render": function ( data, type, full ) {
                if (data < 95) {
                    return '<span class="badge">'+Math.round(data)+'%</span>';
                } else {
                    return '<span class="badge">100%</span>';
                }
            },
            "searchable": false
        },
        {
            "targets": [11],
            "data":"rating_key",
            "visible": false,
            "searchable": false
        },
        {
            "targets": [12],
            "data":"xml",
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
        $('#ajaxMsg').html("<div class='msg'><span class='ui-icon ui-icon-check'></span>Fetching rows...</div>");
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
            data: {row_id: rowData['id'], user: rowData['user']},
            cache: false,
            async: true,
            complete: function(xhr, status) {
                $("#info-modal").html(xhr.responseText);
            }
        });
    }
    showStreamDetails();
});