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
    colors: ['#F9AA03', '#FFFFFF'],
    xAxis: {
            type: 'datetime',
            labels: {
                formatter: function() {
                    return moment(this.value).format("MMM D");
                }
            },
            categories: [{}]
    },
    yAxis: {
            title: {
                text: null
            }
    },
    tooltip: {
        formatter: function() {
            var monthStr = moment(this.x).format("MMM D");
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