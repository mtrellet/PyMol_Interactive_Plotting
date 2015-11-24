var x_analyses_list = [];
var y_analyses_list = [];
var ana_list = [];
var request_ana = {'model':[], 'chain':[], 'residue':[], 'atom':[]};
var stored_plots = {'model':[], 'chain':[], 'residue':[], 'atom':[]};
var counter = [true,true,true,true,true,true,true,true,true];
var url = "http://" + document.domain + ":" + location.port;
var socket = io.connect(url + "/socketio");
var start = 0;
var stop = 0;

$(document).ready(function() {

    window.blockMenuHeaderScroll = false;
    $(window).on('touchstart', function(e)
    {
        if ($(e.target).closest('#model_plots').length == 1)
        {
            blockMenuHeaderScroll = true;
        }
    });
    $(window).on('touchend', function()
    {
        blockMenuHeaderScroll = false;
    });
    $(window).on('touchmove', function(e)
    {
        if (blockMenuHeaderScroll)
        {
            e.preventDefault();
        }
    });

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

    console.log(url);
    socket.on('connect', function() {
        socket.emit('connected',{data: 'I\'m connected!'});
    });

    socket.on('response', function(msg){
        console.log(msg);
    });

    $('form#get_ana').submit(function(event) {
        start = new Date().getTime();
        document.getElementById("ana_button").style.display = 'none';
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
        $("#model_current_plots").append('<b>Current selection: </b>')
        // X AXIS
        var html = '<div id="left_col">\n <p align="left"> X-axis type: \n';
        html+='<select id="model_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select></p>';
        //$("#model_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#model_two_column").append(html);
        var list_x = document.getElementById("model_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        var html = '<div id="right_col">\n <p align="left"> Y-axis type: \n';
        html+='<select id="model_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option></select></p>';
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
        $("#chain_current_plots").append('<b>Current selection: </b>')
        // X AXIS
        var html = '<div id="left_col">\n <p align="left"> X-axis type: \n';
        html+='<select id="chain_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select></p>';
        //$("#chain_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#chain_two_column").append(html);
        var list_x = document.getElementById("chain_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        var html = '<div id="right_col">\n <p align="left"> Y-axis type: \n';
        html+='<select id="chain_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option></select></p>';
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
        $("#residue_current_plots").append('<b>Current selection: </b>')
        // X AXIS
        var html = '<div id="left_col">\n <p align="left"> X-axis type: \n';
        html+='<select id="residue_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select></p>';
        //$("#residue_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#residue_two_column").append(html);
        var list_x = document.getElementById("residue_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        var html = '<div id="right_col">\n <p align="left"> Y-axis type: \n';
        html+='<select id="residue_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option></select></p>';
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
        $("#atom_current_plots").append('<b>Current selection: </b>')
        // X AXIS
        var html = '<div id="left_col">\n <p align="left"> X-axis type: \n';
        html+='<select id="atom_ana_choice_x" onchange="check_x(this);">\n<option value="None" selected>Choose a type</option></select></p>';
        //$("#atom_two_column").append('<div id="left_col">\n<h3> X-axis type: </h3> <br>');
        $("#atom_two_column").append(html);
        var list_x = document.getElementById("atom_ana_choice_x")
        for (i=0; i < msg.data.length; i++) {
            var length = list_x.length;
            list_x[length] = new Option (msg.data[i]);
        }

        // Y AXIS
        var html = '<div id="right_col">\n <p align="left"> Y-axis type: \n';
        html+='<select id="atom_ana_choice_y" onchange="check_y(this);">\n<option value="None" selected>Choose a type</option></select></p>';
        $("#atom_two_column").append(html);
        var list_y = document.getElementById("atom_ana_choice_y")
        for (i=0; i < msg.data.length; i++) {
            var length = list_y.length;
            list_y[length] = new Option (msg.data[i]);
            ana_list.push(msg.data[i])
        }
        $("body").append('<br>');

//        stop = new Date().getTime();
//        var time = stop - start;
//        console.log('Execution time: ' + time);
//
//        y_select.selectedIndex = 0;
//        console.log(request_ana)
//        socket.emit('create', {data: request_ana});
//        return false;
        
        // $("body").append('<br>');

        // stop = new Date().getTime();
        // var time = stop - start;
//        alert('Execution time: ' + time);

    });


    socket.on('new_plot', function(msg){
        console.log(msg);
        create_3djs_plot(msg.data, counter.indexOf(true), msg.lvl)
        counter[counter.indexOf(true)] = false;
        var to_show = document.getElementById("synchro");
        to_show.style.display = '';
//        location.reload(true);
//         stop = new Date().getTime();
//         var time = stop - start;
// //        alert('Execution time: ' + time);

    });
});

function remove_plot(c){
    console.log(counter);
    counter[c] = true;
    console.log(counter);
}

function update_ana(struct_lvl, filters, filters_lvl){
    console.log(stored_plots[struct_lvl]);
    socket.emit('update', {data: stored_plots[struct_lvl], lvl: struct_lvl, filter: filters, filter_lvl: filters_lvl});
}

function send_ana(event){
    start = new Date().getTime();
    var struct_lvl = event.name;
    var x_select = document.getElementById(struct_lvl+"_ana_choice_x")
    if (x_select.value != "None"){
        request_ana[struct_lvl].push(x_select.value)
//        stored_plots[struct_lvl].push(x_select.value)
    }

    var y_select = document.getElementById(struct_lvl+"_ana_choice_y")
    if (y_select.value != "None"){
        request_ana[struct_lvl].push(y_select.value)
//        stored_plots[struct_lvl].push(y_select.value)
    }
    stored_plots[struct_lvl].push([x_select.value, y_select.value]);
    x_select.selectedIndex = 0;
    y_select.selectedIndex = 0;
    console.log(request_ana[struct_lvl])
    socket.emit('create', {data: request_ana[struct_lvl], lvl: struct_lvl});

    $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-2]+" / ");
    $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-1]+" | ");

    document.getElementById(struct_lvl+"_buttons").style.display = "none"
    request_ana[struct_lvl] = [];
}

function expand(elmt){
    to_expand = elmt.nextElementSibling.id;
    if (elmt.nextElementSibling.style.display == "none"){
        elmt.nextElementSibling.style.display = ""
        elmt.style.fontStyle = "normal"
    }
    else{
        elmt.nextElementSibling.style.display = "none"
        elmt.style.fontStyle = "italic"
    }
}

function check_x(choice){
    var struct_lvl = choice.id.substring(0,choice.id.indexOf('_'));
    var y_choice = document.getElementById(struct_lvl+"_ana_choice_y").value;
    if (choice.value != "None" && y_choice != "None") {
        var to_show = document.getElementById(struct_lvl+"_buttons");
        to_show.style.display = '';
    }
}

function check_y(choice){
    var struct_lvl = choice.id.substring(0,choice.id.indexOf('_'));
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
    $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-1]+" / ")

    var y_select = document.getElementById(struct_lvl+"_ana_choice_y")
    request_ana[struct_lvl].push(y_select.value)
    $("#"+struct_lvl+"_current_plots").append(request_ana[struct_lvl][request_ana[struct_lvl].length-1]+" | ")
    console.log(request_ana[struct_lvl]);

    stored_plots[struct_lvl].push([x_select.value, y_select.value]);

    x_select.selectedIndex = 0;
    y_select.selectedIndex = 0;
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
