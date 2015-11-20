var context_colors={
     "none":["white","aliceblue"],
     "weak":["grey","grey"],
     "strong":["black", "black"]
};

var plots = {"model": [], "chain": [], "residue": [], "atom": []};

var lvl_equivalence = {0: "model", 1: "chain", 2: "residue", 3: "atom"};

var lock = false

function create_3djs_plot(filename, counter, level) {

    $("#"+level+"_plots").append('<div id='+level+'_plot_'+counter+' class="plot '+level+'"></div>');
    $("#"+level+"_plot_"+counter).append('<p class="value">Hint: You can click on the dots.</p>');
//    $("#"+level+"_plot_"+counter).append('<form id="destroy" name="'+level+'_plot_'+counter+'" onclick="destroy_plot(this,'+level+','+counter+');"><button type="submit">Destroy</button>')
    var button = '<button name="'+level+'_plot_'+counter+'" onclick="destroy_plot(this.name,\''+level+'\','+counter+')">Destroy</button>';
    $("#"+level+"_plot_"+counter).append(button);

//    $('form#destroy').submit(function(event) {
//        console.log(plots);
//        var plot = event.target.name;
//        document.getElementById(plot).remove();
//        document.getElementById(level+"_current_plots").innerHTML = "";
//        document.getElementById(level+"_buttons").style.display = "none";
//        cur_plot = level+"_plot_"+counter;
//        for(var p = 0; p < plots[level].length; p++){
//            console.log(plots[level][p]);
//            console.log(cur_plot);
//            if (plots[level][p] == cur_plot){
//                delete plots[level][p];
//                p = p-1;
//            }
//        }
//        console.log(plots);
//    });

    console.log(filename);
    console.log(counter);
    console.log(level);

    var getID = function(d) { return "id"+d.id }
    var getX = function(d) { return d.x }
    var getY = function(d) { return d.y }
    var getXtype = function(d) { return d.x_type}
    var getYtype = function(d) { return d.y_type}

    var margin = {top: 30, right: 15, bottom: 20, left: 40},
      width = 500 - margin.left - margin.right,
      height = 300 - margin.top - margin.bottom;

    var x = d3.scale.linear()
      .range([0, width])


    var y = d3.scale.linear()
      .range([height, 0])


    window.svg = d3.select("#"+level+"_plot_"+counter)
      .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      // .append("g")
        .attr("transform",
              "translate("+margin.left + "," + margin.top + ")")
//        .attr("class", counter)
        .attr("id", level+"_svg_"+counter)

    // Define the axes
    var xAxis = d3.svg.axis().scale(x)
      .orient("bottom").ticks(5);

    var yAxis = d3.svg.axis().scale(y)
      .orient("left").ticks(5);

    // var createGraph = function() {
    d3.json("../static/json/"+filename+'?nocache=' + (new Date()).getTime(), function(error, data) {
        if (error){
            console.log(error);
        }
        var x_type = data.type[0].x_type
        var y_type = data.type[0].y_type
        console.log(data.type);
        x.domain(d3.extent(data.values, getX))
        y.domain(d3.extent(data.values, getY))

        d3.select("#"+level+"_svg_"+counter).append("text")
            .attr("class", "x_label")
            .attr("text-anchor", "end")
            .attr("x", width)
            .attr("y", height - 6)
            .text(x_type)
        d3.select("#"+level+"_svg_"+counter).append("text")
            .attr("class", "y_label")
            .attr("text-anchor", "end")
            .attr("y", 6)
            .attr("dy", "0.75em")
            .attr("transform", "rotate(-90)")
            .text(y_type)

        svg.attr("class", filename)

        svg.selectAll(".temp").data(data.values).enter()
          .append("circle")
            .attr("r", 4)
            .attr("id", function(d) { return getID(d) })
            .attr("cx", function(d) { return x(getX(d)) })
            .attr("cy", function(d) { return y(getY(d)) })
            .classed("selected", false)
            .style("fill", context_colors[$('input[name="context_lvl"]:checked').val()][0])
            .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1])
            .on("click", function(d) {
                d3.select("#"+level+"_plot_"+counter+" .value").text("Id: " + d.id + "  "+x_type+": " + d.x +"  "+y_type+": " + d.y);
                var isSelected = d3.select(this).classed("selected");
                d3.select(this)
                  .classed( "selected", !isSelected);
                selected = checkSelected(counter, level, d.id);
//                synchronize_plots(level);
            })
            .on("mouseover", function(d) {
                if(!d3.select(this).classed("selected")){
                    d3.select(this)
                      .style("fill", "blue");
                }
            })
            .on("mouseout", function(d) {
                if(!d3.select(this).classed("selected")){
                    d3.select(this)
                      .style("fill", context_colors[$('input[name="context_lvl"]:checked').val()][0])
                      .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
                }
            })

        // Add the X Axis
        d3.select("#"+level+"_svg_"+counter).append("g")
          .attr("class", "x axis")
          .attr("id", "plot_"+counter)
          .attr("transform", "translate(0," + height + ")")
          .call(xAxis);

        // Add the Y Axis
        d3.select("#"+level+"_svg_"+counter).append("g")
          .attr("class", "y axis")
          .attr("id", "plot_"+counter)
          .call(yAxis);
    })

    var start_select = {x : 0, y : 0}

    d3.select("#"+level+"_svg_"+counter).on( "mousedown", function() {
        var p = d3.mouse( this);
        console.log("DOWN")
        var selected = [];

        if(document.getElementById("sync_plots").checked){
            d3.selectAll("div."+level).selectAll('circle.selected')
              .classed("selected", false)
              .style('fill', context_colors[$('input[name="context_lvl"]:checked').val()][0])
              .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
        }
        else{
            d3.select("#"+level+"_plot_"+counter).selectAll('circle.selected')
              .classed( "selected", false)
              .style('fill', context_colors[$('input[name="context_lvl"]:checked').val()][0])
              .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
        }
        // console.log(test[0].length)
        // test.each(function(data) {
        //   console.log(d3.select(this).classed("selected"))
        // });

        var re = d3.select("#"+level+"_svg_"+counter).select("rect.selection_"+counter)
        if(re.empty()){
            start_select.x = p[0];
            start_select.y = p[1];
            console.log("Selection started");
            d3.select("#"+level+"_svg_"+counter).append( "rect")
            .attr({
              rx      : 6,
              ry      : 6,
              class   : "selection_"+counter,
              x       : p[0],
              y       : p[1],
              width   : 0,
              height  : 0
          })
        }
    })
    .on( "mousemove", function() {
//        var start = new Date().getTime();

        var s = d3.select("#"+level+"_svg_"+counter).select( "rect.selection_"+counter);

        if( !s.empty()) {
            var p = d3.mouse( this),

            d = {
                x       : parseInt( s.attr( "x"), 10),
                y       : parseInt( s.attr( "y"), 10),
                width   : parseInt( s.attr( "width"), 10),
                height  : parseInt( s.attr( "height"), 10)
            },
            move = {
                x : p[0],
                y : p[1]
            };

            if(move.x < start_select.x && move.y >= start_select.y) {
                d.x = move.x;
                d.y = start_select.y;
                d.width = start_select.x - move.x;
                d.height = move.y - start_select.y;
            } else if(move.x < start_select.x && move.y < start_select.y) {
                d.x = move.x;
                d.y = move.y;
                d.width = start_select.x - move.x;
                d.height = start_select.y - move.y;
            } else if(move.x > start_select.x && move.y < start_select.y) {
                d.x = start_select.x;
                d.y = move.y;
                d.width = move.x - start_select.x;
                d.height = start_select.y - move.y;
            } else {
                d.x = start_select.x;
                d.y = start_select.y;
                d.width = move.x - start_select.x;
                d.height = move.y - start_select.y;
            }

            d3.select("#"+level+"_plot_"+counter).selectAll("circle").each(function(data) {
                var circle = {x : d3.select(this).attr("cx"), y : d3.select(this).attr("cy")}
                //console.log(circle)
                if(!d3.select(this).classed("selected") && circle.x >= d.x && circle.x <= d.x+d.width && circle.y >= d.y && circle.y <= d.y+d.height ) {
                    d3.select(this)
                      .classed("selected", true)
                      .style("fill", "blue")
                      .style("stroke", "blue")
                }
                else if (circle.x < d.x || circle.x > d.x+d.width || circle.y < d.y || circle.y > d.y+d.height){
                    d3.select(this)
                      .classed("selected", false)
                      .style("fill", context_colors[$('input[name="context_lvl"]:checked').val()][0])
                      .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
                }
            })

            if (document.getElementById("sync_plots").checked){
                var svgs = d3.selectAll("div."+level);
//                console.log("LEVEL: "+level);
                for(var i = 0; i < svgs[0].length; i++){
                    var plot = svgs[0][i].id
//                    console.log(plot);
                    if (plot.localeCompare("#"+level+"_plot_"+counter) != 0){
                        d3.select("#"+level+"_plot_"+counter).selectAll("circle.selected").each(function(data) {
                            var id = d3.select(this).attr("id");
                            d3.select("#"+plot).select("#"+id)
                              .classed("selected", true)
                              .style("fill", "blue")
                              .style("stroke", "blue")
                        });
                        d3.select("#"+level+"_plot_"+counter).selectAll("circle:not(.selected)").each(function(data) {
                            var id = d3.select(this).attr("id");
                            d3.select("#"+plot).select("#"+id)
                              .classed("selected", false)
                              .style("fill", context_colors[$('input[name="context_lvl"]:checked').val()][0])
                              .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
                        });
                    }
                }
            }
            s.attr( d);
        }

//        var end = new Date().getTime();
//        var time = end - start;

    })

    .on( "mouseup", function() {
        console.log("UP")
        d3.select("#"+level+"_svg_"+counter).select( ".selection_"+counter).remove();
        selected = checkSelected(counter, level);
    });

    svg.on( "touchstart", function() {
        var p = d3.mouse( this);
        console.log("DOWN")
        var selected = [];

        if(document.getElementById("sync_plots").checked){
            d3.selectAll("div."+level).selectAll('circle.selected')
              .classed("selected", false)
              .style('fill', context_colors[$('input[name="context_lvl"]:checked').val()][0])
              .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
        }
        else{
            d3.select("#"+level+"_plot_"+counter).selectAll('circle.selected')
              .classed( "selected", false)
              .style('fill', context_colors[$('input[name="context_lvl"]:checked').val()][0])
              .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
        }

        var re = d3.select("#"+level+"_svg_"+counter).select("rect.selection_"+counter)
        if(re.empty()){
            start_select.x = p[0];
            start_select.y = p[1];
            console.log("Selection started");
            d3.select("#"+level+"_svg_"+counter).append( "rect")
            .attr({
              rx      : 6,
              ry      : 6,
              class   : "selection_"+counter,
              x       : p[0],
              y       : p[1],
              width   : 0,
              height  : 0
          })
        }
    })
    .on( "touchmove", function() {
        var s = d3.select("#"+level+"_svg_"+counter).select( "rect.selection_"+counter);

        if( !s.empty()) {
            var p = d3.mouse( this),
            d = {
                x       : parseInt( s.attr( "x"), 10),
                y       : parseInt( s.attr( "y"), 10),
                width   : parseInt( s.attr( "width"), 10),
                height  : parseInt( s.attr( "height"), 10)
            },
            move = {
                x : p[0],
                y : p[1]
            };

            if(move.x < start_select.x && move.y >= start_select.y) {
                d.x = move.x;
                d.y = start_select.y;
                d.width = start_select.x - move.x;
                d.height = move.y - start_select.y;
            } else if(move.x < start_select.x && move.y < start_select.y) {
                d.x = move.x;
                d.y = move.y;
                d.width = start_select.x - move.x;
                d.height = start_select.y - move.y;
            } else if(move.x > start_select.x && move.y < start_select.y) {
                d.x = start_select.x;
                d.y = move.y;
                d.width = move.x - start_select.x;
                d.height = start_select.y - move.y;
            } else {
                d.x = start_select.x;
                d.y = start_select.y;
                d.width = move.x - start_select.x;
                d.height = move.y - start_select.y;
            }

            d3.select("#"+level+"_plot_"+counter).selectAll("circle").each(function(data) {
                var circle = {x : d3.select(this).attr("cx"), y : d3.select(this).attr("cy")}
                //console.log(circle)
                if(!d3.select(this).classed("selected") && circle.x >= d.x && circle.x <= d.x+d.width && circle.y >= d.y && circle.y <= d.y+d.height ) {
                    d3.select(this)
                      .classed("selected", true)
                      .style("fill", "blue")
                      .style("stroke", "blue")
                }
                else if (circle.x < d.x || circle.x > d.x+d.width || circle.y < d.y || circle.y > d.y+d.height){
                    d3.select(this)
                      .classed("selected", false)
                      .style("fill", context_colors[$('input[name="context_lvl"]:checked').val()][0])
                      .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
                }
            })

            if (document.getElementById("sync_plots").checked){
                var svgs = d3.selectAll("div."+level);
                console.log("LEVEL: "+level);
                for(var i = 0; i < svgs[0].length; i++){
                    var plot = svgs[0][i].id
                    console.log(plot);
                    if (plot.localeCompare("#"+level+"_plot_"+counter) != 0){
                        d3.select("#"+level+"_plot_"+counter).selectAll("circle.selected").each(function(data) {
                            var id = d3.select(this).attr("id");
                            d3.select("#"+plot).select("#"+id)
                              .classed("selected", true)
                              .style("fill", "blue")
                              .style("stroke", "blue")
                        });
                        d3.select("#"+level+"_plot_"+counter).selectAll("circle:not(.selected)").each(function(data) {
                            var id = d3.select(this).attr("id");
                            d3.select("#"+plot).select("#"+id)
                              .classed("selected", false)
                              .style("fill", context_colors[$('input[name="context_lvl"]:checked').val()][0])
                              .style("stroke", context_colors[$('input[name="context_lvl"]:checked').val()][1]);
                        });
                    }
                }
            }

            s.attr( d);
        }
    })
    .on( "touchend", function() {
        d3.select("#"+level+"_svg_"+counter).select( ".selection_"+counter).remove();
        selected = checkSelected(counter, level);
    });

    plots[level].push(level+"_plot_"+counter);
}

function synchronize_plots(level) {
    if(document.getElementById("sync_plots").checked){
        for (var key in lvl_equivalence){
            if (lvl_equivalence[key] == level)
                lvl_num = Number(key);
        }
        destroyed = []
        for(var j = lvl_num+1; j< 4; j++){
            console.log(j+" "+plots[lvl_equivalence[j]].length)
            for(var k = 0 ; k < plots[lvl_equivalence[j]].length ; k++){
                name = plots[lvl_equivalence[j]][k]
                lvl = name.substring(0,name.indexOf('_'));
                c = Number(name.replace(/^\D+/g, ""))
                console.log(name+" "+lvl+" "+c);
                destroyed.push(destroy_plot(plots[lvl_equivalence[j]][k], lvl, c));
                update_plots(lvl, selected, level);
            }
        }
        for(var l = 0 ; l < destroyed.length ; l++){
            cur_plot = destroyed[l];
            idx = plots[level].indexOf(cur_plot);
            if(idx > -1)
                plots[level].splice(idx, 1);
            console.log(plots);
        }
    }
}

function destroy_plot(name,level,counter) {
    console.log(plots);
    var plot = name;
    console.log(name);
    document.getElementById(name).remove();
    console.log(level+"_current_plots");
    document.getElementById(level+"_current_plots").innerHTML = "";
    document.getElementById(level+"_buttons").style.display = "none";
    cur_plot = level+"_plot_"+counter;
    return cur_plot
}


function update_plots(lvl, filter, filter_lvl) {
    console.log(lvl+" "+String(filter)+" "+filter_lvl);
    update_ana(lvl, filter, filter_lvl);
}


function checkSelected(c, level, id) {
    id = typeof id !== 'undefined' ? id : false;
    var list = [];
//    var time = new Date().getTime();
//    alert(time);
    if (id){
        console.log(id);
        $.getJSON('/_uniq_selection', {
            selected: JSON.stringify(id)
        }, function(data){
            console.log(data.result)
            $( "#result").text(data.result);
        });
        list.push(id);
    }
    else{
        d3.select("#"+level+"_plot_"+c).selectAll('circle.selected').each(function(data) {
            list.push(d3.select(this).attr("id").match(/id(\d+)/)[1])
        });
        console.log(list);
        $.getJSON('/_array2python', {
            idlist: JSON.stringify(list),
            plot_level: level
        }, function(data){
            console.log(data.result)
            $( "#result" ).text(data.result);
            synchronize_plots(level);
        });
    }
    console.log("CHECKSELECTED "+list);
    return list;
}



//
//function refreshGraph() {
//  d3.json("../static/json/temperature.json", function(error, data) {
//
//    var vis = d3.select("body");
//
//    // vis.on("click", function () {
//
//    // })
//
//    var newG = vis.selectAll("circle").data(data);
//      newG.enter().append("svg:circle");
//      newG.exit().remove();
//      newG
//        .attr("cx", function(d) { return x(getX(d)) })
//        .attr("cy", function(d) { return y(getY(d)) })
//        .on("click", function(d) {
//          d3.select("#demo .value").text("Id: " + d.id + " "+d.x_type+" " + d.x +": "+d.y_type+": " + d.y)
//        })
//        .on("mouseover", function(d) {
//          d3.select(this)
//            .style("fill", "blue");
//        })
//        .on("mouseout", function(d) {
//          d3.select(this)
//            .style("fill", "grey");
//        })
//  });
//}
    // var svg = d3.select("#demo")
    //     .append("svg:svg")
    // var vis = svg.selectAll("circle").data(data, function(d) { return d.id; })
    // var duration = 200;
    // var delay = 0;

    // // update - This only applies to updating nodes
    // vis.transition()
    //    .duration(duration)
    //    .delay(function(d, i) {delay = i * 7; return delay;})
    //    .attr('transform', function(d) { return 'translate(' + x(getX(d)) + ','
    //       + y(getY(d)) + ')'; })
    //    .attr('r', 4)

    // // enter
    // vis.enter().append('circle')
    //    .attr('transform', function(d) { return 'translate(' + x(getX(d)) + ','
    //       + y(getY(d)) + ')'; })
    //    .attr('r', 4)
    //    .style('opacity', 0)
    //    .transition()
    //    .duration(duration * 1.2)
    //       .style('opacity', 1);

    // // exit
    // vis.exit()
    //    .transition()
    //    .duration(duration + delay)
    //    .style('opacity', 0)
    //    .remove();


  // window.setInterval(function(){
  //   refreshGraph();
  // }, 1000);
