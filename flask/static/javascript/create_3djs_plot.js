function create_3djs_plot(filename, counter) {

    $("#demo").append('<div id="plot_'+counter+'"></div>');
    $("#plot_"+counter).append('<p class="value">Hint: You can click on the dots.</p>');

    console.log(filename);
    console.log(counter);

    var getID = function(d) { return d.id }
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


    window.svg = d3.select("#plot_"+counter)
      .append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      // .append("g")
        .attr("transform",
              "translate("+margin.left + "," + margin.top + ")")
        .attr("class", "id"+counter)

    // Define the axes
    var xAxis = d3.svg.axis().scale(x)
        .orient("bottom").ticks(5);

    var yAxis = d3.svg.axis().scale(y)
        .orient("left").ticks(5);

    // var createGraph = function() {
    var data = d3.json("../static/json/"+filename, function(error, data) {
      if (error){
        console.log(error);
      }
      var x_type = getXtype(data)
      var y_type = getYtype(data)
      x.domain(d3.extent(data, getX))
      y.domain(d3.extent(data, getY))
      svg.selectAll(".temp").data(data).enter()
       .append("circle")
       .attr("r", 4)
       .attr("class", 'temp')
       .attr("id", function(d) { return getID(d) })
       .attr("cx", function(d) { return x(getX(d)) })
       .attr("cy", function(d) { return y(getY(d)) })
       .classed("selected_"+counter, false)
        // .attr("style", "cursor: pointer;")
        .style("fill", "grey")
       .on("click", function(d) {
          d3.select("#plot_"+counter+" .value").text("Id: " + d.id + " "+d.x_type+" " + d.x +": "+d.y_type+": " + d.y);
          var isSelected = d3.select(this).classed( "selected_"+counter);
          d3.select(this)
            .classed( "selected_"+counter, !isSelected);
       })
       .on("mouseover", function(d) {
            if(!d3.select(this).classed("selected_"+counter)){
              d3.select(this)
                .style("fill", "blue");
            }
       })
       .on("mouseout", function(d) {
            if(!d3.select(this).classed("selected_"+counter)){
              d3.select(this)
                .style("fill", "grey");
            }
       })


      // Add the X Axis
      svg.append("g")
          .attr("class", "x axis")
          .attr("transform", "translate(0," + height + ")")
          .call(xAxis);

      // Add the Y Axis
      svg.append("g")
          .attr("class", "y axis")
          .call(yAxis);
    })

    var start_select = {x : 0, y : 0}

    svg.on( "mousedown", function() {
        var p = d3.mouse( this);
        console.log("DOWN")

        d3.selectAll( 'circle').classed( "selected_"+counter, false);
        d3.selectAll('circle').style('fill', 'grey');
        // console.log(test[0].length)
        // test.each(function(data) {
        //   console.log(d3.select(this).classed("selected"))
        // });

        var re = svg.select("rect.selection_"+counter)
        if(re.empty()){
          start_select.x = p[0];
          start_select.y = p[1];
          console.log("Selection started");
          // console.log(p)
          svg.append( "rect")
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
      var s = svg.select( "rect.selection_"+counter);

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
              }
          ;

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

          d3.selectAll("circle").each(function(data) {
            var circle = {x : d3.select(this).attr("cx"), y : d3.select(this).attr("cy")}
            //console.log(circle)
            if(!d3.select(this).classed("selected_"+counter) && circle.x >= d.x && circle.x <= d.x+d.width && circle.y >= d.y && circle.y <= d.y+d.height ) {
              d3.select(this)
                .classed("selected_"+counter, true)
                .style("fill", "blue")
            }
            else if (circle.x < d.x || circle.x > d.x+d.width || circle.y < d.y || circle.y > d.y+d.height){
              d3.select(this)
                .classed("selected_"+counter, false)
                .style("fill", "grey")
            }
          })

          s.attr( d);
          //console.log( d);
      }
    })
    .on( "mouseup", function() {
        svg.select( ".selection_"+counter).remove();
        checkSelected();
    });

    svg.on( "touchstart", function() {
        var p = d3.mouse( this);
        console.log("DOWN")

        d3.selectAll( 'circle').classed( "selected_"+counter, false);
        d3.selectAll('circle').style('fill', 'grey');
        // console.log(test[0].length)
        // test.each(function(data) {
        //   console.log(d3.select(this).classed("selected"))
        // });

        var re = svg.select("rect.selection_"+counter)
        if(re.empty()){
          start_select.x = p[0];
          start_select.y = p[1];
          console.log("Selection started");
          // console.log(p)
          svg.append( "rect")
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
      var s = svg.select( "rect.selection_"+counter);

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
              }
          ;

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

          d3.selectAll("circle").each(function(data) {
            var circle = {x : d3.select(this).attr("cx"), y : d3.select(this).attr("cy")}
            //console.log(circle)
            if(!d3.select(this).classed("selected_"+counter) && circle.x >= d.x && circle.x <= d.x+d.width && circle.y >= d.y && circle.y <= d.y+d.height ) {
              d3.select(this)
                .classed("selected_"+counter, true)
                .style("fill", "blue")
            }
            else if (circle.x < d.x || circle.x > d.x+d.width || circle.y < d.y || circle.y > d.y+d.height){
              d3.select(this)
                .classed("selected_"+counter, false)
                .style("fill", "grey")
            }
          })

          s.attr( d);
          //console.log( d);
      }
    })
    .on( "touchend", function() {
        svg.select( ".selection_"+counter).remove();
        checkSelected();
    });
}

function checkSelected() {
  var list = [];
  d3.selectAll('circle').each(function(data) {
    if(d3.select(this).classed('selected_'+counter)){
      list.push(d3.select(this).attr("id"))
      d3.select(this).style("fill","blue")
    }
  });
  $.getJSON('/_array2python', {
        wordlist: JSON.stringify(list)
    }, function(data){
        console.log(data.result)
        $( "#result" ).text(data.result);
  });
  return false;
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