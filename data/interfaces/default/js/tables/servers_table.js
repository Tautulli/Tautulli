servers_table_options = {
    "language": {
        "search": "Search: ",
        "lengthMenu": "Show _MENU_ entries per page",
        "info": "",
        "infoEmpty": "",
        "infoFiltered": "",
        "emptyTable": "No Servers Defined",
        "loadingRecords": '<div><i class="fa fa-refresh fa-spin"></i> Refreshing Servers...</div>'
    },
    "rowId": 'id',
    "destroy": true,
    "processing": false,
    "serverSide": false,
    "ordering": true,
    "stateSave": false,
    "stateDuration": 0,
    "paging": false,
    "pagingType": "full_numbers",
    "autoWidth": false,
    "searching": false,
    "columnDefs": [
        {
            "targets": "status_tooltip",
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                var active = (rowData['pms_is_enabled']) ? 'active' : '';
                var status = (rowData['pms_is_enabled']) ? 'Enabled' : 'Disabled';
                $(td).html(
                  '<span class="toggle-left trigger-tooltip ' + active + '" data-toggle="tooltip" data-placement="top" title="' + status + '"><i class="fa fa-lg fa-fw fa-server"></i></span>'
                );
            },
            "className": "center",
            "width": "50px",
            "searchable": false,
            "orderable": false
        },
        {
            "targets": "pms_is_enabled",
            "data": "pms_is_enabled",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['pms_is_enabled']) ? 'CHECKED' : '';
                var disabled = (rowData['pms_is_deleted']) ? 'DISABLED' : '';
                $(td).html(
                  '<input type="checkbox" class="pms-is-enabled" id="pms_is_enabled-' + rowData['id'] + '" name="pms_is_enabled-' + rowData['id'] + '" value="1" ' + checked + disabled + '>'
                );
            },
            "className": "center",
            "width": "40px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_name",
            "data": "pms_name",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "75px",
            "searchable": true,
            "orderable": true
        },
        {
            "targets": "pms_ip",
            "data": "pms_ip",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "80px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_port",
            "data": "pms_port",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "40px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_is_remote",
            "data": "pms_is_remote",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['pms_is_remote']) ? 'CHECKED' : '';
                $(td).html('<input type="checkbox" value="1" DISABLED ' + checked + '>');
            },
            "className": "center",
            "width": "20px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_is_cloud",
            "data": "pms_is_cloud",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['pms_is_cloud']) ? 'CHECKED' : '';
                $(td).html('<input type="checkbox" value="1" DISABLED ' + checked + '>');
            },
            "className": "center",
            "width": "40px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_version",
            "data": "pms_version",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "125px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_platform",
            "data": "pms_platform",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "100px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_url",
            "data": "pms_url",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "150px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_identifier",
            "data": "pms_identifier",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "width": "150px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_ssl",
            "data": "pms_ssl",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['pms_ssl']) ? 'CHECKED' : '';
                $(td).html('<input type="checkbox" value="1" DISABLED ' + checked + '>');
            },
            "className": "center",
            "width": "40px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_url_manual",
            "data": "pms_url_manual",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['pms_url_manual']) ? 'CHECKED' : '';
                $(td).html('<input type="checkbox" value="1" DISABLED ' + checked + '>');
            },
            "className": "center",
            "width": "40px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_is_deleted",
            "data": "pms_is_deleted",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['pms_is_deleted']) ? 'CHECKED' : '';
                $(td).html('<input type="checkbox" value="1" DISABLED ' + checked + '>');
            },
            "className": "center",
            "width": "40px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_use_bif",
            "data": "pms_use_bif",
            "createdCell": function (td, cellData, rowData, row, col) {
                var checked = (rowData['pms_use_bif']) ? 'CHECKED' : '';
                $(td).html('<input type="checkbox" value="1" DISABLED ' + checked + '>');
            },
            "className": "center",
            "width": "40px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_web_url",
            "data": "pms_web_url",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_url_override",
            "data": "pms_url_override",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_update_channel",
            "data": "pms_update_channel",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_update_distro",
            "data": "pms_update_distro",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "pms_update_distro_build",
            "data": "pms_update_distro_build",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "no-wrap",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "config-settings",
            "data": null,
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html('<i class="fa fa-lg fa-fw fa-cog"></i>');
                }
            },
            "className": "toggle-right pointer config-settings",
            "width": "20px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "stream_count",
            "data": "stream_count",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "center",
            "width": "75px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "stream_count_direct_play",
            "data": "stream_count_direct_play",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "center",
            "width": "75px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "stream_count_direct_stream",
            "data": "stream_count_direct_stream",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "center",
            "width": "75px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "stream_count_transcode",
            "data": "stream_count_transcode",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    $(td).html(cellData);
                }
            },
            "className": "center",
            "width": "75px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "total_bandwidth",
            "data": "total_bandwidth",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var bw = rowData['total_bandwidth']
                    if (bw > 0) {
                        bw = ((bw > 1000) ? ((bw / 1000).toFixed(1) + ' Mbps') : (bw + ' kbps'));
                    }
                    $(td).html(bw);
                }
            },
            "className": "center",
            "width": "80px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "wan_bandwidth",
            "data": "wan_bandwidth",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var bw = rowData['wan_bandwidth']
                    if (bw > 0) {
                        bw = ((bw > 1000) ? ((bw / 1000).toFixed(1) + ' Mbps') : (bw + ' kbps'));
                    }
                    $(td).html(bw);
                }
            },
            "className": "center",
            "width": "80px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "lan_bandwidth",
            "data": "lan_bandwidth",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    var bw = rowData['lan_bandwidth']
                    if (bw > 0) {
                        bw = ((bw > 1000) ? ((bw / 1000).toFixed(1) + ' Mbps') : (bw + ' kbps'));
                    }
                    $(td).html(bw);
                }
            },
            "className": "center",
            "width": "80px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "server_status",
            "data": "server_status",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                   s = "fa-lg ";
                   t = "fas fa-circle ";
                   c = "white";
                   switch (cellData) {
                      case 0:
                        t = "far fa-circle ";
                        c = "White";
                        sstt = "Server Disabled";
                        break;
                      case 1:
                        c = "Green";
                        sstt = "Server Up";
                        break;
                      case 2:
                        c = "Yellow";
                        sstt = "";
                        break;
                      case 3:
                        c = "Red";
                        sstt = "Server Down";
                        break;
                      default:
                    }
                    $(td).html('<span style="color: ' + c + ';" class="toggle-left trigger-tooltip" data-toggle="tooltip" data-placement="top" title="' + sstt + '"><i class="' + t + s + '"></i></span>');
                }
            },
            "className": "center",
            "width": "50px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "rclone_status",
            "data": "rclone_status",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                   s = "fa-lg ";
                   t = "fas fa-circle ";
                   c = "white";
                   switch (cellData) {
                      case 0:
                        rstt = "Disabled";
                        break;
                      case 1:
                        t = "far fa-circle ";
                        rstt = "Monitoring Disabled";
                        break;
                      case 2:
                        c = "Green";
                        rstt = "rClone Up";
                        break;
                      case 3:
                        c = "Red";
                        rstt = "rClone Down";
                        break;
                      default:
                   }
                   if (cellData === 0) {
                       $(td).html('');
                   } else {
                       $(td).html('<span style="color: ' + c + ';" class="toggle-left trigger-tooltip" data-toggle="tooltip" data-placement="top" title="' + rstt + '"><i class="' + t + s + '"></i></span>');
                   }
                }
            },
            "className": "center",
            "width": "50px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "remote_access_status",
            "data": "remote_access_status",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                   s = "fa-lg ";
                   t = "fas fa-circle ";
                   c = "white";
                   switch (cellData) {
                      case 0:
                        ratt = "Disabled";
                        break;
                      case 1:
                        t = "far fa-circle ";
                        ratt = "Monitoring Disabled";
                        break;
                      case 2:
                        c = "Green";
                        ratt = "remote access Up";
                        break;
                      case 3:
                        c = "Red";
                        ratt = "remote access Down";
                        break;
                      default:
                   }
                   if (cellData === 0) {
                       $(td).html('');
                   } else {
                       $(td).html('<span style="color: ' + c + ';" class="toggle-left trigger-tooltip" data-toggle="tooltip" data-placement="top" title="' + ratt + '"><i class="' + t + s + '"></i></span>');
                   }
                }
            },
            "className": "center",
            "width": "50px",
            "searchable": false,
            "orderable": true
        },
        {
            "targets": "update_available",
            "data": "update_available",
            "createdCell": function (td, cellData, rowData, row, col) {
                if (cellData !== null && cellData !== '') {
                    if (cellData === 1) {
                        $(td).html('<span style="color: white;"><i class="fas fa-check"></i></span>');
                    } else {
                        $(td).html(' ');
                    }
                }
            },
            "className": "center",
            "width": "50px",
            "searchable": false,
            "orderable": true
        },
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
    },
    "preDrawCallback": function(settings) {
    },
    "rowCallback": function (row, rowData) {
    }
}
