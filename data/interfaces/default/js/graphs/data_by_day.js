var hc_data_by_dayofweek_options = {
    chart: {
        type: 'column',
        backgroundColor: 'rgba(0,0,0,0)',
        renderTo: 'chart_div_data_by_dayofweek'
    },
    title: {
        text: ''
    },
    plotOptions: {
            column: {
                pointPadding: 0.2,
                borderWidth: 0
            }
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
            categories: [{}],
            labels: {
                style: {
                    color: '#aaa'
                }
            }
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