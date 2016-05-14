login_table_options = {
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "Showing _START_ to _END_ of _TOTAL_ results",
        "infoEmpty": "Showing 0 to 0 of 0 entries",
        "infoFiltered": "(filtered from _MAX_ total entries)",
        "emptyTable": "No data in table",
        "loadingRecords": '<i class="fa fa-refresh fa-spin"></i> Loading items...</div>'
    },
    "stateSave": true,
    "pagingType": "full_numbers",
    "processing": false,
    "serverSide": true,
    "pageLength": 10,
    "order": [0, 'desc'],
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": "timestamp",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    date = moment(cellData, "X").format(date_format);
                    $(td).html(date);
                } else {
                    $(td).html(cellData);
                }
            },
            "searchable": false,
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [1],
            "data": "timestamp",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    time = moment(cellData, "X").format(time_format);
                    $(td).html(time);
                } else {
                    $(td).html(cellData);
                }
            },
            "searchable": false,
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [2],
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
                        external_ip = '<span class="external-ip-tooltip" data-toggle="tooltip" title="External IP"><i class="fa fa-map-marker fa-fw"></i></span>';
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal">' + external_ip + cellData + '</a>');
                    }
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "20%",
            "className": "no-wrap modal-control-ip"
        },
        {
            "targets": [3],
            "data": "host",
            "width": "20%",
            "className": "no-wrap"
        },
        {
            "targets": [4],
            "data": "os",
            "width": "20%",
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "browser",
            "width": "20%",
            "className": "no-wrap"
        }
    ],
    "drawCallback": function (settings) {
        // Jump to top of page
        // $('html,body').scrollTop(0);

        $('#ajaxMsg').fadeOut();

        // Create the tooltips.
        $('.external-ip-tooltip').tooltip({ container: 'body' });

    },
    "preDrawCallback": function (settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbspFetching rows...";
        showMsg(msg, false, false, 0)
    }
}

$('.login_table').on('click', '> tbody > tr > td.modal-control-ip', function () {
    var tr = $(this).closest('tr');
    var row = login_table.row(tr);
    var rowData = row.data();

    function getUserLocation(ip_address) {
        if (isPrivateIP(ip_address)) {
            return "n/a"
        } else {
            $.ajax({
                url: 'get_ip_address_details',
                data: { ip_address: ip_address },
                async: true,
                complete: function (xhr, status) {
                    $("#ip-info-modal").html(xhr.responseText);
                }
            });
        }
    }
    getUserLocation(rowData['ip_address']);
});