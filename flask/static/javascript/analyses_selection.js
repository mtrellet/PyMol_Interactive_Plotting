var x_analyses_list = [];
var y_analyses_list = [];
var ana_list = [];
var request_ana = [];

$(document).ready(function() {
    var url = "http://" + document.domain + ":" + location.port;
    console.log(url);
    var socket = io.connect(url + "/socketio");
    socket.on('connect', function() {
        socket.emit('connected',{data: 'I\'m connected!'});
    });

    socket.on('response', function(msg){
        console.log(msg);
    });

    $('form#get_ana').submit(function(event) {
        socket.emit('get', {data: 'request'});
        return false;
    });

    socket.on('list_ana', function(msg){
        console.log(msg);
        $("#current_plots").append('<h3>Current selection: <h3>')
        // X AXIS
        var html = '<div id="left_col">\n<h3> X-axis type: </h3>\n';
        html+='<select id="ana_choice_x" onchange="check_x(this.value);">\n<option value="None" selected>Choose a type</option></select>';
        //$("#two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#two_column").append(html);
        var list_x = document.getElementById("ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }
        //$("#two_column").append('</div>');

        // Y AXIS
        html = '<div id="right_col">\n<h3> Y-axis type: </h3>\n';
        html+= '<select id="ana_choice_y" onchange="check_y(this.value);">\n<option value="None" selected>Choose a type</option>></select>';
        $("#two_column").append(html);
        var list_y = document.getElementById("ana_choice_y")
        for (i=0; i < msg.data.length; i++) {
            var length = list_y.length;
            list_y[length] = new Option (msg.data[i]);
            ana_list.push(msg.data[i])
        }
        $("body").append('<br>');
//        html = '<div id="buttons">';
//        html += '<form id="send_ana"> <button type="submit">Create plots</button> </form>';
//        html += '<button onclick="new_ana_lists();">More plot</button>';
//        $("body").append(html);
//        var x_choice = document.getElementById("ana_choice_x");
//        console.log(x_choice.value);
    });

    $('form#send_ana').submit(function(event) {
        console.log(request_ana)
        var x_select = document.getElementById("ana_choice_x")
        if (x_select.value != "None"){
            request_ana.push(x_select.value)
        }
        x_select.selectedIndex = 0;

        var y_select = document.getElementById("ana_choice_y")
        if (y_select.value != "None"){
            request_ana.push(y_select.value)
        }
        y_select.selectedIndex = 0;

        socket.emit('create', {data: request_ana});
        return false;
    });
});

function check_x(val){
    var y_choice = document.getElementById("ana_choice_y").value;
    if (val != "None" && y_choice != "None") {
        var html = '<div id="analysis_buttons"> <br><br> <button onclick="new_ana_lists();">More plot</button>';
        html += '<form id="send_ana"> <button type="submit">Create plots</button> </form>';
        html += '</div>';
//        var div = document.getElementById("two_column");
//        div.innerHTML += html;
        $("body").append(html);
        $("body").append('<br>');
    }
}

function check_y(val){
    var x_choice = document.getElementById("ana_choice_x").value;
    if (val != "None" && x_choice != "None") {
        var html = '<div id="analysis_buttons"> <br><br> <button onclick="new_ana_lists();">More plot</button>';
        html += '<form id="send_ana"> <button type="submit">Create plots</button> </form>';
        html += '</div>';
        //var div = document.getElementById("body");
//        div.innerHTML += html;
        $("body").append(html);
        $("body").append('<br>');
    }
}

function new_ana_lists(){
    var buttons = document.getElementById("analysis_buttons");
    buttons.parentNode.removeChild(buttons);

    var x_select = document.getElementById("ana_choice_x")
    request_ana.push(x_select.value)
    x_select.selectedIndex = 0;
    $("#current_plots").append(request_ana[request_ana.length-1]+" / ")

    var y_select = document.getElementById("ana_choice_y")
    request_ana.push(y_select.value)
    y_select.selectedIndex = 0;
    $("#current_plots").append(request_ana[request_ana.length-1]+"<br>")
}


function get_ana_choices() {
    x_analyses_list = [];
    y_analyses_list = [];
    var x_select = document.getElementById('ana_choice_x');
    for (var i=0, len=x_select.options.length; i<len; i++){
        opt = x_select.options[i];
        if(opt.selected){
            x_analyses_list.push(opt)
        }
    }
    var y_select = document.getElementById('ana_choice_y');
    for (i=0, len=y_select.options.length; i<len; i++){
        opt = y_select.options[i];
        if(opt.selected){
            y_analyses_list.push(opt)
        }
    }
}
