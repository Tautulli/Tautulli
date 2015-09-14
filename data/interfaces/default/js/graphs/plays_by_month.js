var hc_plays_by_month_options = {
    chart: {
        type: 'column',
        backgroundColor: 'rgba(0,0,0,0)',
        renderTo: 'chart_div_plays_by_month'
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
    colors: ['#F9AA03', '#FFFFFF', '#FF4747'],
    xAxis: {
            labels: {
                style: {
                    color: '#aaa'
                }
            },
            categories: [{}]
    },
    yAxis: {
            title: {
                text: null
            },
            labels: {
                style: {
                    color: '#aaa'
                }
            },
            stackLabels: {
                enabled: false,
                style: {
                    color: '#fff'
                }
            }
    },
    plotOptions: {
        column: {
            stacking: 'normal',
            borderWidth: '0',
            dataLabels: {
                enabled: false,
                style: {
                    color: '#000'
                }
            }
        }
    },
    tooltip: {
        shared: true
    },
    series: [{}]
};