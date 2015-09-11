var hc_plays_by_day_options = {
    chart: {
        type: 'line',
        backgroundColor: 'rgba(0,0,0,0)',
        renderTo: 'chart_div_plays_by_day'
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
                        selectHandler(this.category);
                    }
                }
            }
        }
    },
    colors: ['#F9AA03', '#FFFFFF', '#FF4747'],
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
        shared: true
    },
    series: [{}]
};