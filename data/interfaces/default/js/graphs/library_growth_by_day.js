var hc_library_growth_by_day_options = {
    chart: {
        type: 'line',
        backgroundColor: 'rgba(0,0,0,0)',
        renderTo: 'library_growth_by_day'
    },
    title: {
        text: ''
    },
    legend: {
        enabled: true,
        itemStyle: {
            font: '9pt "Open Sans", sans-serif',
            color: '#A0A0A0'
        },
        itemHoverStyle: {
            color: '#FFF'
        },
        itemHiddenStyle: {
            color: '#444'
        }
    },
    credits: {
        enabled: false
    },
    plotOptions: {
        series: {
            allowPointSelect: false,
            threshold: 0,
            events: {
                legendItemClick: function(event) {
                    syncGraphs(this, this.chart.renderTo.id, this.name, event.browserEvent);
                    setGraphVisibility(this.chart.renderTo.id, this.chart.series, this.name);
                }
            }
        }
    },
    xAxis: {
            type: 'datetime',
            labels: {
                formatter: function() {
                    return moment(this.value).format("YY MMM D");
                },
                style: {
                    color: '#aaa'
                }
            },
            categories: [{}],
            plotBands: []
    },
    yAxis: [{
            title: {
                text: null
            },
            labels: {
                style: {
                    color: '#aaa'
                }
            }
    }, {
            title: {
                text: 'Episodes'
            },
            labels: {
                style: {
                    color: '#aaa'
                }
            },
            opposite: true
    }, {
        title: {
            text: 'Tracks'
        },
        labels: {
            style: {
                color: '#aaa'
            }
        },
        opposite: true
    }],
    tooltip: {
        shared: true,
        crosshairs: true
    },
    series: [{}]
};