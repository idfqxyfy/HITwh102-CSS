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
        if (a.classname<b.classname)
            return -1;
        else if (a.classname>b.classname)
            return 1;
        else{
            if(a.start_time<b.start_time) return -1;
            else return 1;
        }
    });
    form.myexperiments = myexperiments;
    for(key in json.all_lessons){
        allexperiments.push(json.all_lessons[key]);
    }
    allexperiments.sort(function (a,b) {
        if (a.teacher.name<b.teacher.name)
            return -1;
        else if (a.teacher.name>b.teacher.name)
            return 1;
        else{
            if(a.classname<b.classname) return -1;
            else if(a.classname>b.classname) return 1;
            else{
                if(a.start_time<b.start_time) return -1;
                else if(a.start_time>=b.start_time) return 1;
            }
        }
    });
    form.allexperiments = allexperiments;
}
$(function () {
    setDate();
    $("#warning button").click(function () {
        $("#board").css("z-index","-1");
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
    $("#sidebar a").click(function (e) {
        e.preventDefault();
        $("html, body").animate({scrollTop: $($(this).attr("href")).offset().top + "px"}, 300);
        return false;
    });
});
var form = new Vue({
    delimiters: ['{[', ']}'],
    el:"#container",
    data:{
        classname:"",
        classroom:"主楼实验室",
        allnumber:"56",
        number:"8",
        telnumber:"",
        time:[{},{},{},{},{},{},{}],
        myexperiments:[],
        allexperiments:[],
        will_change:{},
        new_time:[]
    },
    methods:{
        numberChange:function () {
            var times = Math.ceil(this.allnumber/this.number);
            while (this.time.length !=times ){
                if(this.time.length > times){
                    this.time.pop();
                }
                else {
                    this.time.push({});
                }
            }
        },
        submit:function (e) {
            var passCheck = true;
            e.preventDefault();
            this.time.forEach(function (value) {
                if(!value.hasOwnProperty("week")|!value.week|!value.hasOwnProperty("day")|!value.day|!value.hasOwnProperty("time")|!value.time){
                    passCheck = false;
                }
            });
            if(!this.classname||!this.classroom||!this.telnumber||!this.allnumber) passCheck = false;
            if(passCheck){
                $.ajax({
                    url:"/teacher/",
                    type:"post",
                    data:{
                        "type":"add",
                        "classname":this.classname,
                        "time":this.timelist,
                        "classroom":this.classroom,
                        "tel":this.telnumber,
                        "number":this.number
                    },
                    datatype:"json",
                    success:function (json) {
                        $("#board .text").text("实验添加成功！");
                        $("#board").css("z-index","9999");
                        form.classname = "";
                        form.number = "8";
                        form.time =[{},{},{},{},{},{},{},{}];
                        form.classroom = "主楼实验室";
                        form.telnumber = "";
                        showlesson(json);
                    }
                });
            }
            else{
                $("#board .text").text("请输入所有实验信息！");
                $("#board").css("z-index","9999");
            }
        },
        del:function (e) {
            $.ajax({
                url:"/teacher/",
                type:"post",
                data:{
                    type:"delete",
                    lesson_id:e.id
                },
                success:function (json) {
                    $("#board .text").text("已经将"+ e.classname+"在"+e.start_time+"的实验删掉啦~");
                    $("#board").css("z-index","9999");
                    showlesson(json);
                }
            })
        },
        push_to_change:function (experiment) {
            var time = experiment.start_time.split("，");
            time[0]=time[0].slice(0,-1).slice(1);
            time[1]=time[1].slice(2);
            this.will_change = experiment;
            this.new_time = time;
        },
        cancel:function (e) {
            e.preventDefault();
            this.will_change={};
            this.new_time=[];
        },
        change:function (e) {
            e.preventDefault();
            var newtime = "第" + this.new_time[0] + "周，星期" + this.new_time[1] + "，" + this.new_time[2];
            var oldtime = this.will_change.start_time;
            if (this.will_change.start_time == newtime){
                $("#board .text").text("信息没有变化哦~");
                $("#board").css("z-index","9999");
            }
            else{
                $.ajax({
                url:"/teacher/",
                type:"post",
                data: {
                    "new_time": newtime,
                    "lesson_id":this.will_change.id,
                    "type": "change"
                },
                success:function (json) {
                    form.will_change={};
                    form.new_time=[];
                    $("#board .text").text("时间已从"+ oldtime +"改为" + newtime +"啦~");
                    $("#board").css("z-index","9999");
                    showlesson(json);

                }
            });
            }
        }
    },
    computed:{
        timelist:function () {
            var list ="",str = "";
            this.time.forEach(function (value) {
                str ="第"+ value.week +"周，星期"+ value.day +"，"+ value.time+"/";
                list += str;
            });
            return list;
        }
    },
    created:function () {
        $.ajax({
            url:"/teacher/",
            type:"post",
            data:{
                "type":"get"
            },
            datatype:"json",
            success:function (json) {
                showlesson(json);
                var text = "您好！，" +json.name;
                $("#cookie").text(text);
            },
            error:function () {
                $("#board .text").text("数据请求出现错误，请刷新页面！");
                $("#board").css("z-index","9999");
            }
        })
    }
});