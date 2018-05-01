function setDate(){
    var date = new Date().toLocaleDateString();
    var day = new Date().getDay();
    switch(day){
        case 0:day="星期日";break;
        case 1: day = "星期一"; break;
        case 2: day = "星期二"; break;
        case 3: day = "星期三"; break;
        case 4: day = "星期四"; break;
        case 5: day = "星期五"; break;
        case 6: day = "星期六"; break;
    }
    if (navigator.userAgent.indexOf("compatible") > -1 && navigator.userAgent.indexOf("MSIE") > -1) {
        date = date+ day;
    }
    else if (navigator.userAgent.indexOf('Trident') > -1 && navigator.userAgent.indexOf("rv:11.0") > -1){
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
function prepareform(){
    $("#loginform form").css({
        "opacity":"1",
        "transform": "translateY(0px)"
    });
    $("#sidebar").css({
        "opacity": "1",
    });
    $("#warning button").click(function (e) {
    e.preventDefault();
    $("#warning").css({"opacity":"0","z-index":"-1"});
    });
}
$(function(){
    setDate();
    prepareform();
});
var background = new Vue({
    el: "#background",
    data: {
        imgs: ["../static/image/background1.jpg", "../static/image/background2.jpg", "../static/image/background3.jpg", "../static/image/background4.jpg"],
    },
    computed: {
        preimg: function () {
            return this.imgs[this.imgs.length - 1];
        },
        nextimg: function () {
            return this.imgs[1];
        },
    },
    methods: {
        shownext: function (e) {
            e.preventDefault();
            clearInterval(this.settime);
            $("#background ul").css({
                "transform": "translateX(-66.6%)",
                "transition": "1s",
            });
            $("#shownext").attr("disabled", "disabled");
            var that = this;
            setTimeout(function (){
                that.imgs.push(that.imgs.shift());
                $("#background ul").css({
                    "transform": "translateX(-33.3%)",
                    "transition": "0s"
                });
                $("#shownext").removeAttr("disabled");
               that.settime = setInterval(function () {
                    $("#shownext").trigger("click");
                }, 10000);
            }, 1100);
        },
        showpre: function (e) {
            e.preventDefault();
            clearInterval(this.settime);
            $("#background ul").css({
                "transform": "translateX(0)",
                "transition": "1s"
            });
            $("#showpre").attr("disabled", "disabled");
            var that = this;
            setTimeout(function (){
                that.imgs.unshift(that.imgs.pop());
                $("#background ul").css({
                    "transform": "translateX(-33.3%)",
                    "transition": "0s"
                })
                $("#showpre").removeAttr("disabled");
                that.settime = setInterval(function () {
                    $("#shownext").trigger("click");
                }, 10000);
            }, 1100);
        }
    },
    mounted: function () {
        this.settime = setInterval(function () {
            $("#shownext").trigger("click");
        }, 10000);
    },
});
var form = new Vue({
    el: "#loginform",
    data: {
        username: "",
        password: "",
        nameerror:false,
        pswderror:false,
    },
    methods: {
        checkusername:function(){
            if (!/^\d{2}$/.test(this.username)&&!/^\d{2}102\d{4}$/.test(this.username)&&this.username.length!=0) this.nameerror=true;
            else this.nameerror = false;
        },
        checkpassword:function () {
            if (!/^\w{6,12}$/.test(this.password)&&this.password.length!=0) this.pswderror = true;
            else this.pswderror = false;
        },
         submit:function(e){
            e.preventDefault();
            $.ajax({
                url:"/",
                type:"post",
                data:{
                    "username":parseInt(this.username),
                    "password":this.password,
                },
                success:function(json){
                    json = JSON.parse(json);
                    if(json.result =="success"){
                        $("#warning .text").text("登录成功").parent().css({"opacity":"1","z-index":"9999"});
                        setTimeout(function () {
                            if(json.identify=="teacher"){
                                window.location.assign( "/teacher/");
                            }
                            else {
                                window.location.assign( "/student/");
                            }
                        },300);
                    }
                    else if(json.result =="unexist"){
                        $("#warning .text").text("账号不存在哦~").parent().css({"opacity":"1","z-index":"9999"});
                        form.password = "";
                    }
                    else if(json.result =="wrong"){
                        $("#warning .text").text("密码有误呀~").parent().css({"opacity":"1","z-index":"9999"});
                        form.password = "";
                    }
                    else if(json.result =="wait"){
                        $("#warning .text").text("邮箱还没有激活哦~").parent().css({"opacity":"1","z-index":"9999"});
                        form.password = "";
                    }
                    else if(json.result =="error"){
                        $("#warning .text").text("出现了未知错误哦~，请检查输入或者启用cookie").parent().css({"opacity":"1","z-index":"9999"});
                        form.password = "";
                    }
                }
            })
        }
    },
    computed: {
       error:function(){
           return (this.nameerror || this.pswderror || this.username.length == 0 || this.password.length == 0);
       },
       style:function(){
           if (!this.error) return {
               cursor: "pointer"
                              };
            else return {
               backgroundColor:"gray"
            }
       }
    }
});
