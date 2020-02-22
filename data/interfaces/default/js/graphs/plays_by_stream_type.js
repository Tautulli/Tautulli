var hc_plays_by_stream_type_options = {
    chart: {
        type: 'line',
        backgroundColor: 'rgba(0,0,0,0)',
        renderTo: 'graph_plays_by_stream_type'
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
            cursor: 'pointer',
            point: {
                events: {
                    click: function() {
                        selectHandler(this.category, this.series.name);
                    }
                }
            },
            events: {
                legendItemClick: function() {
                    setGraphVisibility(this.chart.renderTo.id, this.chart.series, this.name);
                }
            }
        }
    },
    colors: ['#E5A00D', '#FFFFFF', '#F06464'],
    xAxis: {
            type: 'datetime',
            labels: {
                formatter: function() {
                    return moment(this.value).format("MMM D");
                },
                style: {
                    color: '#aaa'
                }
            },
            categories: [{}],
            plotBands: []
    },
    yAxis: {
            title: {
                text: null
            },
            labels: {
                style: {
                    color: '#aaa'
                }
            }
    },
    tooltip: {
        shared: true,
        crosshairs: true
    },
    series: [{}]
};