$.fn.dataTableExt.afnSortData['dom-data-order'] = function  ( oSettings, iColumn )
    {
        return $.map( oSettings.oApi._fnGetTrNodes(oSettings), function (tr, i) {
            return $('td:eq('+iColumn+')', tr).attr('data-order');
        } );
    }