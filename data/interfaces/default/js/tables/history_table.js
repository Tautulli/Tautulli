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
    "pagingType": "bootstrap",
    "stateSave": true,
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [ 1, 'desc'],
    "autoWidth": false,
    "columnDefs": [
        {
            "targets": [1],
            "data":"date",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (rowData['stopped'] === null) {
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
                    if (rowData['user_id']) {
                        $(td).html('<a href="user?user_id=' + rowData['user_id'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('<a href="user?user=' + rowData['user'] + '">' + cellData + '</a>');
                    }
                } else {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [3],
            "data":"player",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html('<a href="#" data-target="#info-modal" data-toggle="modal"><i class="fa fa-lg fa-info-circle"></i></a>&nbsp'+cellData);
                }
            },
            "className": "modal-control no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [4],
            "data":"ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData) {
                    if (isPrivateIP(cellData)) {
                        if (cellData != '') {
                            $(td).html(cellData);
                        } else {
                            $(td).html('n/a');
                        }
                    } else {
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal"><i class="fa fa-map-marker"></i>&nbsp' + cellData +'</a>');
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "className": "no-wrap hidden-xs modal-control-ip"
        },
        {
            "targets": [5],
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
            "targets": [6],
            "data":"started",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null) {
                    $(td).html('n/a');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "className": "no-wrap hidden-sm hidden-xs"
        },
        {
            "targets": [7],
            "data":"paused_counter",
            "render": function ( data, type, full ) {
                if (data !== null) {
                    return Math.round(moment.duration(data, 'seconds').as('minutes')) + ' mins';
                } else {
                    return '0 mins';
                }
            },
            "searchable": false,
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [8],
            "data":"stopped",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData === null) {
                    $(td).html('n/a');
                } else {
                    $(td).html(moment(cellData,"X").format(time_format));
                }
            },
            "searchable": false,
            "className": "no-wrap hidden-md hidden-xs"
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
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [10],
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
            "orderable": false,
            "className": "no-wrap hidden-md hidden-xs",
            "width": "10px"
        },
        {
            "targets": [0],
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                $(td).html('<button class="btn btn-xs btn-danger" data-id="' + rowData['id'] + '"><i class="fa fa-trash-o"></i> Delete</button>');
            },
            "className": "delete-control no-wrap hidden",
            "searchable": false,
            "orderable": false
        },
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();
        // Create the tooltips.
        $('.info-modal').each(function() {
            $(this).tooltip();
        });
        if ($('#row-edit-mode').hasClass('active')) {
            $('.delete-control').each(function() {
                $(this).removeClass('hidden');
            });
        }
    },
    "preDrawCallback": function(settings) {
        var msg = "<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>";
        showMsg(msg, false, false, 0)
    }
}

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

$('#history_table').on('click', 'td.modal-control-ip', function () {
    var tr = $(this).parents('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    function getUserLocation(ip_address) {
        if (isPrivateIP(ip_address)) {
            return "n/a"
        } else {
            $.ajax({
                url: 'get_ip_address_details',
                data: {ip_address: ip_address},
                async: true,
                complete: function(xhr, status) {
                    $("#ip-info-modal").html(xhr.responseText);
                }
            });
        }
    }
    getUserLocation(rowData['ip_address']);
});

$('#history_table').on('click', 'td.delete-control', function () {
    var tr = $(this).parents('tr');
    var row = history_table.row( tr );
    var rowData = row.data();

    $(this).children("button").prop('disabled', true);
    $(this).children("button").html('<i class="fa fa-spin fa-refresh"></i> Delete');

    $.ajax({
        url: 'delete_history_rows',
        data: {row_id: rowData['id']},
        async: true,
        success: function(data) {
            history_table.ajax.reload(null, false);
        }
    });

});