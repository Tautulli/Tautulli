user_ip_table_options = {
    "responsive": {
        details: false
    },
    "destroy": true,
    "language": {
        "search": "Search: ",
        "lengthMenu":"Show _MENU_ entries per page",
        "info":"Showing _START_ to _END_ of _TOTAL_ results",
        "infoEmpty":"Showing 0 to 0 of 0 entries",
        "infoFiltered":"(filtered from _MAX_ total entries)",
        "emptyTable": "No data in table",
    },
    "stateSave": false,
    "sPaginationType": "bootstrap",
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
            "className": "no-wrap"
        },
        {
            "targets": [1],
            "data":"ip_address",
            "width": "15%",
            "className": "modal-control no-wrap",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (isPrivateIP(cellData)) {
                    if (cellData != '') {
                        $(td).html(cellData);
                    } else {
                        $(td).html('n/a');
                    }
                } else {
                    $(td).html('<a href="#ip-info-modal" data-toggle="modal"><span data-toggle="ip-tooltip" data-placement="left" title="IP Address Info" id="ip-info"><i class="icon-map-marker icon-white"></i></span>&nbsp' + cellData +'</a>');
                }
            },
            "width": "15%"
        },
        {
            "targets": [2],
            "data":"play_count",
            "width": "10%"
        },
        {
            "targets": [3],
            "data":"platform",
            "width": "15%"
        },
        {
            "targets": [4],
            "data":"last_watched",
            "width": "30%"
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

$('#user_ip_table').on('mouseenter', 'td.modal-control span', function () {
    $(this).tooltip();
});

$('#user_ip_table').on('click', 'td.modal-control', function () {
    var tr = $(this).parents('tr');
    var row = user_ip_table.row( tr );
    var rowData = row.data();

    function getUserLocation(ip_address) {
        if (isPrivateIP(ip_address)) {
            return "n/a"
        } else {
            $.ajax({
                url: 'http://ip-api.com/json/' + ip_address,
                cache: true,
                async: true,
                type: 'GET',
                dataType: 'json',
                success: function(data) {
                    $('#modal_header_ip_address').html(ip_address);
                    $('#country').html(data.country);
                    $('#city').html(data.city);
                    $('#region').html(data.regionName);
                    $('#timezone').html(data.timezone);
                    $('#lat').html(data.lat);
                    $('#lon').html(data.lon);
                    $('#isp').html(data.isp);
                    $('#org').html(data.org);
                    $('#as').html(data.as);
                }
            });
        }
    }

    getUserLocation(rowData['ip_address']);
});