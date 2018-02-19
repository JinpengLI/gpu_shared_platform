function estimate_price(){
    var cpu_cores = $("#cpu_cores").val();
    var mem = $("#mem").val();
    var gpu_mem = $("#gpu_mem").val();
    var disk_size = $("#disk_size").val();
    var hdd_disk_size = $("#hdd_disk_size").val();
    var get_url = "estimate_price?cpu_cores=" + cpu_cores + "&mem="+mem+"&gpu_mem="+gpu_mem+"&disk_size="+disk_size+"&hdd_disk_size="+hdd_disk_size;
    console.log(get_url);
    $.ajax({
       type: 'GET',
       url: get_url,
       //data: {cat_name:name,cat_desc:desc}, //How can I preview this?
       //dataType: 'json',
       async: false, //This is deprecated in the latest version of jquery must use now callbacks
       success: function(result){
           console.log(result);
           $("#price_input").val(result.price);
       }
     });
}

setTimeout(function(){
   estimate_price();
}, 3000);


