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
    colors: ['#F9AA03', '#FFFFFF'],
    xAxis: {
            type: 'datetime',
            labels: {
                formatter: function() {
                    return moment(this.value).format("MMM YYYY");
                },
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
                enabled: true,
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
        formatter: function() {
            var monthStr = moment(this.x).format("MMM YYYY");
            var s = '<b>'+ monthStr +'</b>';

            $.each(this.points, function(i, point) {
                s += '<br/>'+point.series.name+': '+point.y;
            });
            return s;
        },
        shared: true
    },
    series: [{}]
};