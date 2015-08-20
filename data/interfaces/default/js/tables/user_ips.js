user_ip_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ results",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"(filtered from _MAX_ total entries)",
        "emptyTable": "No data in table",
    },
    "stateSave": true,
    "pagingType": "bootstrap",
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "order": [ 0, 'desc'],
    "autoWidth": false,
    "columnDefs": [
        {
            "targets": [0],
            "data":"last_seen",
            "render": function ( data, type, full ) {
                return moment(data, "X").fromNow();
            },
            "searchable": false,
            "width": "15%",
            "className": "no-wrap hidden-xs"
        },
        {
            "targets": [1],
            "data": "ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData) {
                    if (isPrivateIP(cellData)) {
                        if (cellData != '') {
                            $(td).html(cellData);
                        } else {
                            $(td).html('n/a');
                        }
                    } else {
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal"><span data-toggle="ip-tooltip" data-placement="left" title="IP Address Info" id="ip-info"><i class="fa fa-map-marker"></i></span>&nbsp' + cellData +'</a>');
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "15%",
            "className": "no-wrap modal-control-ip"
        },
        {
            "targets": [2],
            "data":"platform",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData) {
                    $(td).html('<a href="#" data-target="#info-modal" data-toggle="modal"><i class="fa fa-lg fa-info-circle"></i>&nbsp' + cellData + '</a>');
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "15%",
            "className": "no-wrap hidden-md hidden-sm hidden-xs modal-control"
        },
        {
            "targets": [3],
            "data":"last_watched",
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
                    } else if (rowData['media_type']) {
                        $(td).html('<a href="info?item_id=' + rowData['id'] + '">' + cellData + '</a>');
                    } else {
                        $(td).html('n/a');
                    }
                }
            },
            "className": "hidden-sm hidden-xs"
        },
        {
            "targets": [4],
            "data":"play_count",
            "searchable": false,
            "width": "10%"
            }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);
        $('#ajaxMsg').fadeOut();
        // Create the tooltips.
        $('.info-modal').each(function () {
            $(this).tooltip();
        });
    },
    "preDrawCallback": function(settings) {
        var msg = "<div class='msg'><i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...</div>";
        showMsg(msg, false, false, 0)
    }
}

$('#user_ip_table').on('mouseenter', 'td.modal-control span', function () {
    $(this).tooltip();
});

$('#user_ip_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = user_ip_table.row(tr);
    var rowData = row.data();

    function showStreamDetails() {
        $.ajax({
            url: 'get_stream_data',
            data: { row_id: rowData['id'], user: rowData['friendly_name'] },
            cache: false,
            async: true,
            complete: function (xhr, status) {
                $("#info-modal").html(xhr.responseText);
            }
        });
    }
    showStreamDetails();
});

$('#user_ip_table').on('click', 'td.modal-control-ip', function () {
    var tr = $(this).parents('tr');
    var row = user_ip_table.row( tr );
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