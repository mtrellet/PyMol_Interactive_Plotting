var x_analyses_list = [];
var y_analyses_list = [];
var ana_list = [];
var request_ana = {'model':[], 'chain':[], 'residue':[], 'atom':[]};
var counter = 0;

$(document).ready(function() {

    var to_hide = document.getElementById("model_buttons");
    to_hide.style.display = 'none';
    to_hide = document.getElementById("chain_buttons");
    to_hide.style.display = 'none';
    to_hide = document.getElementById("residue_buttons");
    to_hide.style.display = 'none';
    to_hide = document.getElementById("atom_buttons");
    to_hide.style.display = 'none';

    to_hide = document.getElementById("synchro");
    to_hide.style.display = 'none';

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

    $('input[type=radio][name=context_lvl]').change(function() {
        console.log($('input[name="context_lvl"]:checked').val());
        socket.emit('update_context', {data: $('input[name="context_lvl"]:checked').val()});
    });

    ////////////////// MODEL //////////////////

    socket.on('list_model_ana', function(msg){
        console.log(msg);
        $("#model_current_plots").append('<h3>Current selection: <h3>')
        // X AXIS
        var html = '<div id="left_col">\n<h3> X-axis type: </h3>\n';
        html+='<select id="model_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select>';
        //$("#model_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#model_two_column").append(html);
        var list_x = document.getElementById("model_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        html = '<div id="right_col">\n<h3> Y-axis type: </h3>\n';
        html+= '<select id="model_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option>></select>';
        $("#model_two_column").append(html);
        var list_y = document.getElementById("model_ana_choice_y")
        for (i=0; i < msg.data.length; i++) {
            var length = list_y.length;
            list_y[length] = new Option (msg.data[i]);
            ana_list.push(msg.data[i])
        }
        $("body").append('<br>');
    });

    ////////////////// CHAIN //////////////////

    socket.on('list_chain_ana', function(msg){
        console.log(msg);
        $("#chain_current_plots").append('<h3>Current selection: <h3>')
        // X AXIS
        var html = '<div id="left_col">\n<h3> X-axis type: </h3>\n';
        html+='<select id="chain_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select>';
        //$("#chain_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#chain_two_column").append(html);
        var list_x = document.getElementById("chain_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        html = '<div id="right_col">\n<h3> Y-axis type: </h3>\n';
        html+= '<select id="chain_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option>></select>';
        $("#chain_two_column").append(html);
        var list_y = document.getElementById("chain_ana_choice_y")
        for (i=0; i < msg.data.length; i++) {
            var length = list_y.length;
            list_y[length] = new Option (msg.data[i]);
            ana_list.push(msg.data[i])
        }
        $("body").append('<br>');
    });

    ////////////////// RESIDUE //////////////////

    socket.on('list_residue_ana', function(msg){
        console.log(msg);
        $("#residue_current_plots").append('<h3>Current selection: <h3>')
        // X AXIS
        var html = '<div id="left_col">\n<h3> X-axis type: </h3>\n';
        html+='<select id="residue_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select>';
        //$("#residue_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#residue_two_column").append(html);
        var list_x = document.getElementById("residue_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        html = '<div id="right_col">\n<h3> Y-axis type: </h3>\n';
        html+= '<select id="residue_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option>></select>';
        $("#residue_two_column").append(html);
        var list_y = document.getElementById("residue_ana_choice_y")
        for (i=0; i < msg.data.length; i++) {
            var length = list_y.length;
            list_y[length] = new Option (msg.data[i]);
            ana_list.push(msg.data[i])
        }
        $("body").append('<br>');
    });

    ////////////////// ATOM //////////////////

    socket.on('list_atom_ana', function(msg){
        console.log(msg);
        $("#atom_current_plots").append('<h3>Current selection: <h3>')
        // X AXIS
        var html = '<div id="left_col">\n<h3> X-axis type: </h3>\n';
        html+='<select id="atom_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select>';
        //$("#atom_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#atom_two_column").append(html);
        var list_x = document.getElementById("atom_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        html = '<div id="right_col">\n<h3> Y-axis type: </h3>\n';
        html+= '<select id="atom_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option>></select>';
        $("#atom_two_column").append(html);
        var list_y = document.getElementById("atom_ana_choice_y")
        for (i=0; i < msg.data.length; i++) {
            var length = list_y.length;
            list_y[length] = new Option (msg.data[i]);
            ana_list.push(msg.data[i])
        }
        $("body").append('<br>');
    });


    $('form#send_ana').submit(function(event) {
        var struct_lvl = event.target.name;
        var x_select = document.getElementById(struct_lvl+"_ana_choice_x")
        if (x_select.value != "None"){
            request_ana[struct_lvl].push(x_select.value)
        }
        x_select.selectedIndex = 0;

        var y_select = document.getElementById(struct_lvl+"_ana_choice_y")
        if (y_select.value != "None"){
            request_ana[struct_lvl].push(y_select.value)
        }
        y_select.selectedIndex = 0;
        console.log(request_ana[struct_lvl])
        socket.emit('create', {data: request_ana[struct_lvl], lvl: struct_lvl});

        $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-1]+" / ");
        $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-1]+"<br>");

        document.getElementById(struct_lvl+"_buttons").style.display = "none"

        request_ana[struct_lvl] = [];
        return false;
    });

    socket.on('new_plot', function(msg){
        console.log(msg);
//        var body = document.getElementsByTagName('body')[0];
//        var script = document.createElement('script');
//        script.type = 'text/javascript';
//        script.src = 'static/javascript/analyses_selection.js';
//        // To pass arguments: http://stackoverflow.com/questions/9642205/how-to-force-a-script-reload-and-re-execute
//        script.class = msg.data[0];
//        body.insertBefore(script, body.firstChild);
        create_3djs_plot(msg.data, counter, msg.lvl)
        counter += 1;
        var to_show = document.getElementById("synchro");
        to_show.style.display = '';
//        location.reload(true);
    });
});

function check_x(choice){
    var struct_lvl = choice.id.substring(0,choice.id.indexOf('_'));
    console.log(struct_lvl);
    var y_choice = document.getElementById(struct_lvl+"_ana_choice_y").value;
    if (choice.value != "None" && y_choice != "None") {
        var to_show = document.getElementById(struct_lvl+"_buttons");
        to_show.style.display = '';
    }
}

function check_y(choice){
    var struct_lvl = choice.id.substring(0,choice.id.indexOf('_'));
    console.log(struct_lvl);
    var x_choice = document.getElementById(struct_lvl+"_ana_choice_x").value;
    if (choice.value != "None" && x_choice != "None") {
        var to_show = document.getElementById(struct_lvl+"_buttons");
        to_show.style.display = '';
    }
}

function new_ana_lists(choice){
    var struct_lvl = choice.id.substring(0,choice.id.indexOf('_'));
    console.log(struct_lvl);
    var buttons = document.getElementById(struct_lvl+"_buttons");
    buttons.style.display = 'none';

    var x_select = document.getElementById(struct_lvl+"_ana_choice_x")
    request_ana[struct_lvl].push(x_select.value)
    x_select.selectedIndex = 0;
    $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-1]+" / ")

    var y_select = document.getElementById(struct_lvl+"_ana_choice_y")
    request_ana[struct_lvl].push(y_select.value)
    y_select.selectedIndex = 0;
    $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-1]+"<br>")
    console.log(request_ana[struct_lvl]);
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
