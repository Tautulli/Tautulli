//php-cpu-monitor was developed by Steve Stone - zyk0tik@gmail.com
//If you find this useful then please share it about to people who you think may also find use for it.
//This program comes with absolutely no warranty and under no license. 
//If you think you can contribute to the codebase then please contact me!

//Enables Tooltips using JQueryUI.
$(function() {
     $( document ).tooltip({
          track: true,
          show: false,
          hide: false
     });
});
//Enables Tabs using JQueryUI.
$(function() {
     $( "#tabs" ).tabs();
});

var cpuUsage = new Array, ramUsage = new Array, cpuWidth = new Array, ramWidth = new Array, cpuCall = "0.5";

//Function to change how often the monitor is refreshed           
function changeSeconds(){
     if ($("#radio1").attr("checked")) {
          cpuCall = "1";
          $("#timeBox").html("1 Second");
     }else if ($("#radio5").attr("checked")){
          cpuCall = "5";
          $("#timeBox").html("5 Seconds");
     }else if ($("#radio01").attr("checked")){
          cpuCall = "0.1";
          $("#timeBox").html("0.1 Seconds");
     }else if ($("#radio10").attr("checked")){
          cpuCall = "10";
          $("#timeBox").html("10 Seconds");
     }else{
          cpuCall = "0.5";
          $("#timeBox").html("0.5 Seconds");
     }
}

//Function to process data and draw the graph in the browser
$(function replay(){
     //Loads div with current CPU usage and does not continue with the function until it is complete.
     $("#cpu").load("cpu.php?cpu=" + cpuCall , function() {
          //Loads div with current RAM usage and does not continue with the function until it is complete.
          $("#ram").load("cpu.php", function(){
               for (i=0; i<39; i++){
                    //Sets all values in an array with previous CPU and RAM information. This is done on a sliding scale so previous value for array[10] becomes the new value for array[9] and so on.
                    cpuUsage[i] = cpuUsage[i + 1];
                    cpuWidth[i] = cpuWidth[i + 1];
                    ramUsage[i] = ramUsage[i + 1];
                    ramWidth[i] = ramWidth[i + 1];
               }
               //Sets the values of the highest number in the array to the current value. Also sets the titles of things to current value and also tells it what height the bars in the graph should be.
               cpuUsage[39] = $("#cpu").html();
               $("#cpuO").html(cpuUsage[39]);
               cpuWidth[39] = cpuUsage[39] * 2.3 + 5, 10;
               ramUsage[39] = $("#ram").html();
               $("#ramO").html(ramUsage[39]);
               ramWidth[39] = ramUsage[39] * 2.3 + 5, 10;
               for(i=0; i<40; i++){
                    //Does all the changes of bar heights in the graph. the ,0 at the end means do it in 0 miliseconds. This can be changed if you want to see the bars slide up and down.
                    $("#cpu" + i).animate({
                         height: cpuWidth[i] * 2.2,
                    },0);
                    $("#ram" + i).animate({
                         height: ramWidth[i] * 2.2,
                    },0);
                    $("#cpuO" + i).animate({
                         height: cpuWidth[i],
                    },0);
                    $("#ramO" + i).animate({
                         height: ramWidth[i],
                    },0);
                    //Sets all of the tooltips for the bars so when you highlight them it shows you what percentage was in use at that time.
                    $("#cpu" + i).attr('title', cpuUsage[i] + '%');
                    $("#ram" + i).attr('title', ramUsage[i] + '%');
                    $("#cpuO" + i).attr('title', cpuUsage[i] + '%');
                    $("#ramO" + i).attr('title', ramUsage[i] + '%');
               }
               //Once the function has completed it calls itself again.
               replay();
          });
     });
});


