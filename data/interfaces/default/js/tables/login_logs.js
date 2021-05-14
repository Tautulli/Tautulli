login_log_table_options = {
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
    "stateDuration": 0,
    "pagingType": "full_numbers",
    "processing": false,
    "serverSide": true,
    "pageLength": 25,
    "order": [0, 'desc'],
    "autoWidth": false,
    "scrollX": true,
    "columnDefs": [
        {
            "targets": [0],
            "data": "timestamp",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== '') {
                    $(td).html(moment(cellData, "X").format('YYYY-MM-DD HH:mm:ss'));
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
            "data": "friendly_name",
            "width": "10%",
            "className": "no-wrap"
        },
        {
            "targets": [2],
            "data": "user_group",
            "width": "7%",
            "className": "no-wrap"
        },
        {
            "targets": [3],
            "data": "ip_address",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData) {
                    isPrivateIP(cellData).then(function () {
                        $(td).html(cellData || 'n/a');
                    }, function () {
                        external_ip = '<span class="external-ip-tooltip" data-toggle="tooltip" title="External IP"><i class="fa fa-map-marker fa-fw"></i></span>';
                        $(td).html('<a href="javascript:void(0)" data-toggle="modal" data-target="#ip-info-modal">' + external_ip + cellData + '</a>');
                    });
                } else {
                    $(td).html('n/a');
                }
            },
            "width": "10%",
            "className": "no-wrap modal-control-ip"
        },
        {
            "targets": [4],
            "data": "host",
            "width": "18%",
            "className": "no-wrap"
        },
        {
            "targets": [5],
            "data": "os",
            "width": "15%",
            "className": "no-wrap"
        },
        {
            "targets": [6],
            "data": "browser",
            "width": "15%",
            "className": "no-wrap"
        },
        {
            "targets": [7],
            "data": "expiry",
            "createdCell": function (td, cellData, rowData, row, col) {
                var active = '';
                if (rowData['current']) {
                    active = '<span class="current-tooltip" data-toggle="tooltip" title="Current Session"><i class="fa fa-lg fa-fw fa-check-circle"></i></span>&nbsp;';
                }
                if (cellData) {
                    var signout = '&nbsp;<span class="sign-out-tooltip" data-toggle="tooltip" title="Sign Out"><i class="fa fa-lg fa-fw fa-sign-out-alt"></i></span>';
                    $(td).html(active + cellData + signout);
                } else if (rowData['success']) {
                    $(td).html('expired');
                }
            },
            "searchable": false,
            "className": "no-wrap",
            "width": "13%"
        },
        {
            "targets": [8],
            "data": "success",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData == 1) {
                    $(td).html('<span class="success-tooltip" data-toggle="tooltip" title="Login Successful"><i class="fa fa-lg fa-fw fa-check"></i></span>');
                } else {
                    $(td).html('<span class="success-tooltip" data-toggle="tooltip" title="Login Failed"><i class="fa fa-lg fa-fw fa-times"></i></span>');
                }
            },
            "searchable": false,
            "orderable": false,
            "className": "no-wrap",
            "width": "2%"
        },
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

    },
    "preDrawCallback": function (settings) {
        var msg = "<i class='fa fa-refresh fa-spin'></i>&nbsp; Fetching rows...";
        showMsg(msg, false, false, 0)
        $('[data-toggle="tooltip"]').tooltip('destroy');
    }
};

$('.login_log_table').on('click', '> tbody > tr > td.modal-control-ip', function () {
    var tr = $(this).closest('tr');
    var row = login_log_table.row(tr);
    var rowData = row.data();

    $.get('get_ip_address_details', {
        ip_address: rowData['ip_address']
    }).then(function (jqXHR) {
        $("#ip-info-modal").html(jqXHR);
    });
});

$('.login_log_table').on('click', '> tbody > tr > td> .sign-out-tooltip', function () {
    var tr = $(this).closest('tr');
    var row = login_log_table.row(tr);
    var rowData = row.data();

    $.get('logout_user_session', {
        row_ids: rowData['row_id'],
        current: rowData['current']
    }).then(function () {
        if (rowData['current']) {
            window.location = 'auth/logout';
        } else {
            login_log_table.draw();
        }
    });
});
