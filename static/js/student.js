function setDate() {
    var date = new Date().toLocaleDateString();
    var day = new Date().getDay();
    switch (day) {
        case 0: day = "星期日"; break;
        case 1: day = "星期一"; break;
        case 2: day = "星期二"; break;
        case 3: day = "星期三"; break;
        case 4: day = "星期四"; break;
        case 5: day = "星期五"; break;
        case 6: day = "星期六"; break;
    }
    if (navigator.userAgent.indexOf("compatible") > -1 && navigator.userAgent.indexOf("MSIE") > -1) {
        date = date + day;
    }
    else if (navigator.userAgent.indexOf('Trident') > -1 && navigator.userAgent.indexOf("rv:11.0") > -1) {
        date = date + day;
    }
    else if (navigator.userAgent.indexOf('Edge')>-1){
        date = date + day;
    }
    else {
        date = date.split("/");
        date = date[0] + "年" + date[1] + "月" + date[2] + "日" + " " + day;
    }
    $("#date").text(date);
}
function showlesson(json) {
    var myexperiments=[],allexperiments=[],key;
    for(key in json.my_lessons){
        myexperiments.push(json.my_lessons[key]);
    }
    myexperiments.sort(function (a,b) {
        a=a.start_time.split(",");
        b=b.start_time.split(",");
        if (parseInt(a[0].slice(0,-1).slice(1))<parseInt(b[0].slice(0,-1).slice(1))) return -1;
        else if(parseInt(a[0].slice(0,-1).slice(1))>parseInt(b[0].slice(0,-1).slice(1))) return 1;
        else{
            if(a[1]<b[1]) return -1;
            else if (a[1]>b[1]) return 1;
            else{
                if(a[2]>b[2]) return 1;
                else return -1;
            }
        }
    });
    form.myexperiments = myexperiments;
    for(key in json.all_lessons){
        allexperiments.push(json.all_lessons[key]);
    }
    allexperiments.sort(function (a,b) {
        if(a.classname<b.classname) return -1;
        else if(a.classname>b.classname) return 1;
        else {
            a=a.start_time.split(",");
            b=b.start_time.split(",");
            if (parseInt(a[0].slice(0,-1).slice(1))<parseInt(b[0].slice(0,-1).slice(1))) return -1;
            else if(parseInt(a[0].slice(0,-1).slice(1))>parseInt(b[0].slice(0,-1).slice(1))) return 1;
            else{
                if(a[1]<b[1]) return -1;
                else if (a[1]>b[1]) return 1;
                else{
                    if(a[2]>b[2]) return 1;
                    else return -1;
                }
            }
        }
    });
    if(allexperiments.length>0){
        json.all_lessons = {};
        allexperiments.forEach(function (value) {
        if(!json.all_lessons.hasOwnProperty(value.classname)){
            json.all_lessons[value.classname]={
                showed:false,
                classroom:value.classroom,
                teacher:value.teacher.name,
                tel:value.tel,
                lessons:[value]
            }
        }
        else {
            json.all_lessons[value.classname].lessons.push(value);
        }
    });
        if(myexperiments.length>0){
            myexperiments.forEach(function (value) {
                if(json.all_lessons.hasOwnProperty(value.classname)){
                json.all_lessons[value.classname].selected = true;
                }
            });
        }
    }
    else{
        form.allexperiments=null;
        return ;
    }
    var temp={};
    for( key in json.all_lessons){
        if(json.all_lessons[key].selected != true) temp[key] = json.all_lessons[key];
    }
    for( key in json.all_lessons){
        if(json.all_lessons[key].selected == true) temp[key] = json.all_lessons[key];
    }
    form.allexperiments = temp;
}
$(function () {
    setDate();
    $("#warning button").click(function () {
        $("#board").css({"z-index":"-1","opacity":"0"});
    });
    $("#logout").click(function (e) {
        e.preventDefault()
        $.ajax({
            url:"/logout/",
            type:"get",
            success:function (json) {
                    window.location.assign("/");
            }
        });
    });
});
var form = new Vue({
    delimiters: ['{[', ']}'],
    el:"#container",
    data:{
        myexperiments:[],
        allexperiments:{}
    },
    methods:{
        del:function (experiment) {
            $.ajax({
                url:"/student/",
                type:"post",
                data:{
                    "type":"unselect",
                    "lesson_id":experiment.id
                },
                success:function (json) {
                    showlesson(json);
                    $("#board .text").text("取消成功！");
                    $("#board").css({"z-index":"9999","opacity":"1"});
                }
            });
        },
        add:function (experiment) {
            $.ajax({
                url:"/student/",
                type:"post",
                data:{
                    "type":"select",
                    "lesson_id":experiment.id
                },
                success:function (json) {
                    showlesson(json);
                    $("#board .text").text("添加成功！");
                    $("#board").css({"z-index":"9999","opacity":"1"});
                }
            });
        },
        showup:function (key) {
            this.allexperiments[key].showed=true;
        }
    },
    created:function () {
        $.ajax({
            url:"/student/",
            type:"post",
            data:{
                "type":"get"
            },
            success:function (json) {
                showlesson(json);
                $("#cookie").text("您好！，"+json.name);
            }
        });
    }
});