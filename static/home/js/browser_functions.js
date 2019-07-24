function superposition(oTable, columns, site, hide_first_column) {
    // oTable: DataTable object of table of entries
    // columns: Column indeces of oTable to be extracted to build table for reference selection. First column has to be structure/model string used for superposition workflow
    // site: Structure browser or Homology model browser (add new logic when expanding to new sites)
    if(window.location.hash === "#keepselection") {}
    else {
        ClearSelection('targets');
        ClearSelection('reference');
    }

    var checked_data = oTable.rows('.alt_selected').data();
    if (checked_data.length===0) {
        window.alert('No entries selected for superposition')
        return 0;
    }
    var selected_ids = []
    if (site==='structure_browser') {
        for (i = 0; i < checked_data.length; i++) {
            var div = document.createElement("div");
            div.innerHTML = checked_data[i][6];
            if (typeof div.innerText !== "undefined") {
                selected_ids.push(div.innerText.replace(/\s+/g, ''));
            } else {
                selected_ids.push(div.textContent.replace(/\s+/g, ''));
            }
        }
        AddToSelection('targets', 'structure_many', selected_ids.join(","));
    } else if (site==='homology_model_browser') {
        for (i = 0; i < checked_data.length; i++) {
            var div = document.createElement("div");
            div.innerHTML = checked_data[i][12];
            var state = checked_data[i][3];
            if (checked_data[i][4]==='Yes') {
                div.innerHTML = checked_data[i][11];
                if (typeof div.innerText !== "undefined") {
                    selected_ids.push(div.innerText.replace(/\s+/g, '')+"_refined");
                } else {
                    selected_ids.push(div.textContent.replace(/\s+/g, '')+"_refined");
                }
            }
            else {
                if (typeof div.innerText !== "undefined") {
                    selected_ids.push(div.innerText.replace(/\s+/g, '')+"_"+state);
                    console.log(div.textContent.replace(/\s+/g, '')+"_"+state);
                } else {
                    selected_ids.push(div.textContent.replace(/\s+/g, '')+"_"+state);
                    console.log(div.textContent.replace(/\s+/g, '')+"_"+state);
                }
            }
        }
        AddToSelection('targets', 'structure_models_many', selected_ids.join(","));
    } // add new logic here for new site

    $('#modal_table tbody').empty();
    var modal = document.getElementById('myModal');
    var span = document.getElementsByClassName("close")[0];
    modal.classList.add("modal");
    // console.log('hasclass',$('#myModal').hasClass('modal'));
    // console.log(modal);
    modal.style.display = "block";
    span.onclick = function() {
        modal.style.display = "none";
    }
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    }
    var checked_data = oTable.rows('.alt_selected').data();
    // var needed_columns = [6,1,2,3,4,5,10,26]
    for (i=0; i<checked_data.length; i++) {
        var div = document.createElement("div");
        row = document.createElement('tr');
        var checkbox = document.createElement('input');
        checkbox.type = "checkbox";
        row.appendChild(checkbox);
        var column_count = 0;
        columns.forEach(function(column) {
            div.innerHTML = checked_data[i][column];
            cell = document.createElement('td');
            textnode = document.createTextNode(div.innerText.replace(/\s+/g, ''));
            if(column_count===0 && typeof hide_first_column==="undefined") {}
            else if (column_count===0 && hide_first_column===true) {
                cell.style.display = "none";
            }
            cell.appendChild(textnode);
            row.appendChild(cell);
            column_count++;
        });
        $('#modal_table tbody').append(row)
    }
    $('#modal_table tbody tr').click(function() {
        if (site==='structure_browser') {
            AddToSelection('reference', 'structure', $(this).children().eq(1).text());
        } else if (site==='homology_model_browser') {
            console.log($(this).children().eq(9));
            console.log($(this).children().eq(8));
            if ($(this).children().eq(9).text()==='Yes') {
                AddToSelection('reference', 'structure',  $(this).children().eq(11).text()+"_refined");
                console.log($(this).children().eq(11).text()+"_refined");
            }
            else {
                var state = $(this).children().eq(8).text();
                AddToSelection('reference', 'structure_model', $(this).children().eq(1).text()+"_"+state);
                console.log($(this).children().eq(1).text()+"_"+state);
            }
        } // Add logic here for new site
        $(this).children(':first').prop("checked",true);
        window.location.href = '/structure/superposition_workflow_index';
    })
};

function Sort(clicked_th, table1, table2) {
    if (clicked_th.parent().parent().parent().attr('class').includes('scrollable')) {
        var table = table1;
    }
    else if (clicked_th.parent().parent().parent().attr('class').includes('frozen')) {
        var table = table2;
    }
    if (clicked_th.attr('class').includes('asc')) {
        table.order([clicked_th.index(),'asc']);
    }
    else if (clicked_th.attr('class').includes('desc')) {
        table.order([clicked_th.index(),'desc']);
    }
    table.draw();
}

function ClearSelection(selection_type) {
    $.ajax({
        'url': '/common/clearselection',
        'data': {
            selection_type: selection_type
        },
        'type': 'GET',
        'async': false,
        'success': function (data) {
            $("#selection-" + selection_type).html(data);
        }
    });
}

function AddToSelection(selection_type, selection_subtype, selection_id) {
    $.ajax({
        'url': '/common/addtoselection',
        'data': {
            selection_type: selection_type,
            selection_subtype: selection_subtype,
            selection_id: selection_id
        },
        'type': 'GET',
        'async': false,
        'success': function(data) {
            $("#selection-" + selection_type).html(data);
        },
    });
}

function select_all(e, table1_id, table2_id) {
    $('#loading_div').show();
    var rows = $("#"+table1_id).dataTable().$('tr', {filter:"applied"});
    var checkedStatus = $(e).prop("checked");
    $(rows).each(function() {
        if (this.hidden==false) {
            $(this).prop("checked", checkedStatus);
            $(this).eq(0).toggleClass('alt_selected', checkedStatus);
            // if (checkedStatus==true) {
            $(this).find(":checkbox").prop("checked", checkedStatus)
            // }
            // $(this).find(":checkbox").trigger('click');
        }
    });
    $('#loading_div').hide();
};

function assign_to_row1(table1_id, table2_id){
  $('#'+table1_id+' > tbody > tr').click(function(event) {
    if (event.target.type !== 'checkbox') {
        $(':checkbox', this).trigger('click');
        $(':checkbox', $("#"+table2_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]")).trigger('click');
        $(this).eq(0).toggleClass('alt_selected');
        console.log($(this).eq(0));
    }
    else {
        $(this).eq(0).toggleClass('alt_selected');
    }
  });
}

function assign_to_row2(table1_id, table2_id){
  $('#'+table2_id+' > tbody > tr').click(function(event) {
    if (event.target.type !== 'checkbox') {
        $(':checkbox', this).trigger('click');
        $(':checkbox', $("#"+table1_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]")).trigger('click');
        $("#"+table1_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").eq(0).toggleClass('alt_selected');
        console.log($("#"+table1_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").eq(0));
    }
    else {
        $("#"+table1_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").eq(0).toggleClass('alt_selected');
    }
  });
}

function match_rowheight(table1_id, table2_id) {
    $("#"+table2_id).find('tr').each(function(i, e) {
        $("#"+table1_id).find('tr').eq(i).height($(this).height());
    });
    $("#"+table1_id).find('tr').each(function(i, e) {
        $("#"+table2_id).find('tr').eq(i).height($(this).height());
    });
}

var trigger_draw = true

function catch_filter(table1_id, table2_id, oTable1, oTable2) {
    if (trigger_draw==true) {
        $('#'+table2_id).on( 'draw.dt', function (e,oSettings) {
            $('#loading_div').show();
            update_tables(table1_id, table2_id, 2);
            var scrollable_height = $('.yadcf-datatables-table--'+table2_id+' > thead > tr').eq(1).eq(0).height();
            $('.yadcf-datatables-table--'+table1_id+' > thead > tr').eq(1).css('height', scrollable_height);
            $('#loading_div').hide();
        });
        $('#'+table1_id).on( 'draw.dt', function (e,oSettings) {
            $('#loading_div').show();
            update_tables(table1_id, table2_id, 1);
            var frozen_height = $('.yadcf-datatables-table--'+table1_id+' > thead > tr').eq(1).eq(0).height();
            $('.yadcf-datatables-table--'+table2_id+' > thead > tr').eq(1).css('height', frozen_height);
            trigger_draw = false;
            oTable2.draw();
            trigger_draw = true;
            $('#loading_div').hide();
        });
    }
}

function update_tables(table1_id, table2_id, source_table) {
    if (source_table===2) {
        $('#'+table1_id+' > tbody > tr').prop('hidden', true);
        ids = Array();
        var rows = $("#"+table2_id).dataTable().$('tr', {filter:"applied"});
        rows.each(function(i,e) {
            $("#"+table1_id+" > tbody > tr[model_id=" + $(e).attr('model_id') + "]").attr('class', $(e).attr('class'));
            $("#"+table1_id+" > tbody > tr[model_id=" + $(e).attr('model_id') + "]").prop('hidden', false);
        });
    }
    else if (source_table===1) {
        $('#'+table2_id+' > tbody > tr').prop('hidden', true);
        ids = Array();
        var rows = $("#"+table1_id).dataTable().$('tr', {"filter":"applied"});
        rows.each(function(i,e) {
            $("#"+table2_id+" > tbody > tr[model_id=" + $(e).attr('model_id') + "]").attr('class', $(e).attr('class'));
            $("#"+table2_id+" > tbody > tr[model_id=" + $(e).attr('model_id') + "]").prop('hidden', false);
        });
    }
}

//Match row highlight in other table
function match_row_highlight(table1_id, table2_id) {
    var prev_index = -1;
    $('#'+table2_id+' > tbody > tr').mouseover(function(){
        if (prev_index!==$(this).index()){
            $(this).css('background-color','rgb(245,245,245)');
            $("#"+table1_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").css('background-color','rgb(245,245,245)');
        }
        prev_index = $(this).index();
    });
    $('#'+table1_id+' > tbody > tr').mouseover(function(){
        if (prev_index!==$(this).index()){
            $(this).css('background-color','rgb(245,245,245)');
            $("#"+table2_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").css('background-color','rgb(245,245,245)');
        }
        prev_index = $(this).index();
    });
    $('#'+table2_id+' > tbody > tr').mouseout(function(){
        if ($(this).hasClass('odd')){
            $(this).css('background-color','rgb(249,249,249)');
            $("#"+table1_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").css('background-color','rgb(249,249,249)');
        }
        else if ($(this).hasClass('even')){
            $(this).css('background-color','rgb(255,255,255)');
            $("#"+table1_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").css('background-color','rgb(255,255,255)');
        }
    });
    $('#'+table1_id+' > tbody > tr').mouseout(function(){
        if ($(this).hasClass('odd')){
            $(this).css('background-color','rgb(249,249,249)');
            $("#"+table2_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").css('background-color','rgb(249,249,249)');
        }
        else if ($(this).hasClass('even')){
            $(this).css('background-color','rgb(255,255,255)');
            $("#"+table2_id+" > tbody > tr[model_id=" + $(this).attr('model_id') + "]").css('background-color','rgb(255,255,255)');
        }
    });
}

//Matching scrolls
function match_scroll_position() {
    var tables = document.querySelectorAll(".dataTables_scrollBody");
    var frozen_table = tables[0];
    var scrollable_table = tables[1];

    var isLeftScrollTopCalled = false;
    $(frozen_table).scroll(function (e) {
        if (isRightScrollTopCalled) {
            return isRightScrollTopCalled = false;
        }
        $(scrollable_table).scrollTop($(this).scrollTop());
        isLeftScrollTopCalled = true;
    });

    var isRightScrollTopCalled = false;
    $(scrollable_table).scroll(function (e) {
        if (isLeftScrollTopCalled) {
            return isLeftScrollTopCalled = false;
        }
        $(frozen_table).scrollTop($(this).scrollTop());
        isRightScrollTopCalled = true;
    });
}