from datetime import datetime
from email.mime import application
import imp
from pickle import NONE
import random
from urllib import response
from bs4 import BeautifulSoup
from django.shortcuts import render, HttpResponse, redirect
from django.contrib import auth
from django.urls import reverse
from tuanzi.Myforms import AvatarForm, UserForm, ChangePasswordForm
from tuanzi.models import Applications, Post, Post2Tag, Tag, UserInfo, following
from tuanzi.utils import validCode
from tuanzi import models
import json
from django.http import JsonResponse
from django.db.models import F, Count
from django.db.models.functions import TruncMonth
from django.db import transaction
from django.contrib.auth.decorators import login_required
import os
from xiaotuan import settings
from django.core.paginator import Paginator
import random
from datetime import datetime
from django.db.models import Q


def login(request):
    """
    登录视图函数:
       get请求响应页面
       post(Ajax)请求响应字典
       response返回错误信息
    """

    if request.method == "POST":

        response = {"user": None, "msg": None}      # json文件，用于记录信息返回，提升用户体验
        user = request.POST.get("user")
        pwd = request.POST.get("pwd")
        valid_code = request.POST.get("valid_code")
        valid_code_str = request.session.get("valid_code_str")
        
        if valid_code.upper() == valid_code_str.upper():        # 大小写不区分认证
            user = auth.authenticate(username=user, password=pwd)
            
            if user:
                auth.login(request, user)       # request.user== 当前登录对象
                response["user"] = user.username
            else:
                response["msg"] = "用户名或者密码错误!"

        else:
            response["msg"] = "验证码错误!"

        return JsonResponse(response)

    return render(request, "login.html")


def get_valid_code_img(request):
    """
    基于PIL模块动态生成响应状态码图片
    """
    img_data = validCode.get_valid_code_img(request)

    return HttpResponse(img_data)


def logout(request):
    """
    注销视图
    """
    auth.logout(request)  

    return redirect("/login/")


def index(request, x, pindex=1):
    """
    系统首页
    :param request:
    :return:
    """
    mywhere = ""        # 用于记录搜索关键词
    search = request.GET.get("keyword", None)
    countpost = 2       # 保证随机数范围，后续对随机函数了解加深需要优化

    if x == 2:      # 搜索标签时
        k = x
        if search is not None:
            taglist = models.Tag.objects.filter(title__icontains=search).all()
            allp2tlist = []
            allpost_list = []
            
            for tag in taglist:
                p2tlist = models.Post2Tag.objects.filter(tag=tag)
                allp2tlist += p2tlist

            for p2t in allp2tlist:
                p_list = models.Post.objects.filter(nid=p2t.post.nid)
                allpost_list += p_list
            
            mywhere = "keyword=" + (search)
            countpost = len(allp2tlist)


        else:
            allpost_list = models.Post.objects.all()
            countpost = len(allpost_list)

    elif x == 1:        # 搜索标题时
        k = x
        if search is not None:
            allpost_list = models.Post.objects.filter(title__icontains=search).all()
            mywhere = "keyword=" + (search)
            countpost = len(allpost_list)
        
        else:
            allpost_list = models.Post.objects.all()
            countpost = len(allpost_list)

    else:
        allpost_list = models.Post.objects.all()
        countpost = len(models.Post.objects.all())

    allpost_list = list(reversed(allpost_list))
    
    p = Paginator(allpost_list, 5)      # 用于分页功能
    if pindex < 1:
        pindex = 1

    if pindex > p.num_pages:
        pindex = p.num_pages

    pagerange = p.page_range        
    post_list = p.page(pindex)
    
    op = []     # 获得随机浏览功能中的帖子数据，保险起见选择使用链表
    while not op:
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost + 2)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]
    
    
    status = UserInfo.objects.get(nid=request.session.get('_auth_user_id')).status      # 获取用户状态，团长拥有特权      
    if status == 3:
        status3 = 1
    else:
        status3 = 0
    return render(request, "index.html", locals())


def searchtag(request):
    """
    搜索标签函数:
    """
    
    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]

    tag_list = models.Tag.objects.all()     # 获取标签信息，用于搜索
    return render(request, 'searchtag.html', locals())


def register(request):
    """
    注册视图函数:
       get请求响应注册页面
       post(Ajax)请求,校验字段,响应字典
    """

    if request.is_ajax():
        form = UserForm(request.POST)

        response = {"user": None, "msg": None}
        if form.is_valid():
            response["user"] = form.cleaned_data.get("user")

            # 生成一条用户纪录
            user = form.cleaned_data.get("user")
            pwd = form.cleaned_data.get("pwd")
            email = form.cleaned_data.get("email")
            avatar_obj = request.FILES.get("avatar")

            extra = {}      #上传头像时使用django更为便捷的功能，不用判断不上传时使用default的情况
            if avatar_obj:
                extra["avatar"] = avatar_obj

            user_obj = UserInfo.objects.create_user(username=user, password=pwd, email=email, **extra)
            user_obj.save()

        else:
            response["msg"] = form.errors

        return JsonResponse(response)

    form = UserForm()
    return render(request, "register.html", {"form": form})


def createpost(request):
    """
    创建帖子视图函数:
       get请求响应注册页面
       post(Ajax)请求,校验字段,响应字典
    """
    
    if request.method == "POST":
        title = request.POST.get("title")
        content = request.POST.get("content")

        # 防止xss攻击,过滤script标签
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup.find_all():
            if tag.name == "script":
                tag.decompose()

        ob = models.Post.objects.create(title=title, content=str(soup), user=request.user)

        tagtitle = request.POST.get("tag")      # 表情名
        if not models.Tag.objects.filter(title=tagtitle).all():
            currenttag = Tag()
            currenttag.title = tagtitle
            currenttag.save()
        else:
            currenttag = models.Tag.objects.filter(title=tagtitle).all()[0]
            currenttag.save()

        newp2t = Post2Tag()     # 建立帖子和标签的联系
        newp2t.tag = currenttag
        newp2t.post = ob
        newp2t.save()

        return redirect("/index/1/1")
    return render(request, "createpost.html")


def post_detail(request, username, post_id):
    """
    帖子详情页视图
    """

    #获取帖子信息
    user = UserInfo.objects.filter(username=username).first()
    post_obj = models.Post.objects.filter(pk=post_id).first()
    page = post_id
    comment_list = models.Comment.objects.filter(post_id=post_id)

    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]
    return render(request, "post_detail.html", locals())


def digg(request):
    """
    点赞功能
    """

    post_id = request.POST.get("post_id")
    is_up = json.loads(request.POST.get("is_up"))  # "true"值判断赞或踩
    
    # 点赞人即当前登录人
    user_id = request.user.pk
    obj = models.PostUpDown.objects.filter(user_id=user_id, post_id=post_id).first()

    response = {"state": True}
    if not obj:
        ard = models.PostUpDown.objects.create(user_id=user_id, post_id=post_id, is_up=is_up)

        queryset = models.Post.objects.filter(pk=post_id)
        if is_up:
            queryset.update(up_count=F("up_count") + 1)
        else:
            queryset.update(down_count=F("down_count") + 1)
    else:
        response["state"] = False
        response["handled"] = obj.is_up

    return JsonResponse(response)       # response提示一个人只能点一次


def comment(request):
    """
    提交评论视图函数
    功能:
    1 保存评论
    2 回复评论
    """
    post_id = request.POST.get("post_id")
    pid = request.POST.get("pid")
    content = request.POST.get("content")
    user_id = request.user.pk

    post_obj = models.Post.objects.filter(pk=post_id).first()

    # 根目录操作
    with transaction.atomic():
        comment_obj = models.Comment.objects.create(user_id=user_id, post_id=post_id, content=content,
                                                    parent_comment_id=pid)
        models.Post.objects.filter(pk=post_id).update(comment_count=F("comment_count") + 1)

    response = {}

    response["create_time"] = comment_obj.create_time.strftime("%Y-%m-%d %X")
    response["username"] = request.user.username
    response["content"] = content

    return JsonResponse(response)


def get_comment_tree(request):
    """
    获取评论树视图函数
    """
    post_id = request.GET.get("post_id")
    response = list(models.Comment.objects.filter(post_id=post_id).order_by("pk").values("pk", "content",
                                                                                         "parent_comment_id"))

    return JsonResponse(response, safe=False)


def modifya(request):
    """
    修改头像视图函数
    """

    # 获取头像提交表单
    if request.is_ajax():
        form = AvatarForm(request.POST, user=request.user)
        response = {"msg": None}    

        if form.is_valid():
            user = request.user
            avatar_obj = request.FILES.get("avatar")

            if avatar_obj:
                user.avatar = avatar_obj
                user.save()

        else:
            response["msg"] = form.errors

        return JsonResponse(response)
    else:
        form = UserForm()


    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]
    return render(request, "modifya.html", locals())


def cgpwd(request):
    """
    修改密码视图函数
    """

    if request.is_ajax():
        form = ChangePasswordForm(request.POST, user=request.user)  # 获取form表单
        response = {"msg": None}

        # 获取更改密码表单
        if form.is_valid():
            user = request.user
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password']
            user.set_password(new_password)
            user.save()
            auth.logout(request)        # 修改成功后自动退出

        else:
            response["msg"] = form.errors

        return JsonResponse(response)

    else:
        form = ChangePasswordForm()

    op = []     # 出现多次是因为随机浏览需要获取帖子信息，进一步优化会考虑全局变量
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]

    return render(request, 'cgpwd.html', locals())


def createp2t(request):
    """
    新增标签视图函数
    """

    # 获取标签表单
    if request.method == "POST":
        posttitle = request.POST.get("title")
        ob = models.Post.objects.filter(title=posttitle).all()[0]

        tagtitle = request.POST.get("tag")

        currenttag = Tag()
        currenttag.title = tagtitle
        currenttag.save()

        # 建立标签和帖子联系
        newp2t = Post2Tag()
        newp2t.tag = currenttag
        newp2t.post = ob
        newp2t.save()
        response = {"msg": "i"}
        return JsonResponse(response)

    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]

    return render(request, "createp2t.html",locals())


def clubinfo(request, username):
    """
    社团主页视图函数
    """

    userid = request.session.get('_auth_user_id')
    xisfollow = models.following.objects.filter(Q(club__username=username) & Q(fan__nid=userid)).first()    # 判断是否关注
    currentclub = models.UserInfo.objects.filter(username=username).first()
    post_list = models.Post.objects.filter(user__username=username).all()

    allpost_list = models.Post.objects.all()
    p = Paginator(allpost_list, 5)

    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]
    return render(request, "clubinfo.html", locals())


def followta(request, clubid):
    """
    关注功能函数
    """

    # 建立社团与成员之前的关注关系
    userid = request.session.get('_auth_user_id')
    currentfan = models.UserInfo.objects.filter(nid=userid).first()
    currentidol = models.UserInfo.objects.filter(nid=clubid).first()
    currentidolusername = currentidol.username
    ob = following()
    ob.club = currentidol
    ob.fan = currentfan
    ob.save()

    return redirect('/clubinfo/%s' % (currentidolusername))


def myidol(request):
    """
    关注人的帖子查看函数
    """

    #通过过滤获取关注人信息
    userid = request.session.get('_auth_user_id')
    followinglist = models.following.objects.filter(fan__nid=userid).all()
    idollist = []
    for ifollowing in followinglist:
        idollist.append(ifollowing.club)

    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]
    return render(request, "myidol.html", locals())


def createapplication(request):
    """
    申请成为社团视图函数
    """
    
    if request.method == "POST":
        ob = Applications()
        content = request.POST.get("content")
        
        #防止xss注入攻击
        soup = BeautifulSoup(content, "html.parser")
        for tag in soup.find_all():
            if tag.name == "script":
                tag.decompose()
        
        ob.content = str(soup)
        nid = request.session.get('_auth_user_id')
        user = UserInfo.objects.get(pk=nid)
        user.status = 2
        user.save()
        ob.user = user
        ob.save()
        return redirect("/index/1/1")

    nid = request.session.get('_auth_user_id')
    user = UserInfo.objects.get(pk=nid)
    
    status = user.status                #获取成员当前状态
    statuslist = [0, 0, 0, 0]
    statuslist[status - 1] = 1         
    status1 = statuslist[0]
    status2 = statuslist[1]
    status3 = statuslist[2]
    status4 = statuslist[3]

    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]

    return render(request, "createapplication.html", locals())


def hotrank(request, pindex=1):
    """
    热门排行视图函数
    """
    
    allpost_list = models.Post.objects.all().order_by('-up_count')          # 目前热度算法采用最简单的按点赞数，后续可能会更进更加实用的热度算法
    p = Paginator(allpost_list, 5)

    if pindex < 1:
        pindex = 1

    if pindex > p.num_pages:
        pindex = p.num_pages

    countpost = len(models.Post.objects.all())
    post_list = p.page(pindex)
    
    op = []
    while not op:
        countpost = len(models.Post.objects.all())
        random.seed(datetime.now())
        rangepost_id = random.randint(1, countpost)
        op = models.Post.objects.filter(nid=rangepost_id)
    op = op[0]
    
    status = UserInfo.objects.get(nid=request.session.get('_auth_user_id')).status
    if status == 3:
        status3 = 1
    else:
        status3 = 0

    return render(request, "hotrank.html", locals())


def upload(request):
    """
    富文本编辑器上传视图函数
    """

    img_obj = request.FILES.get("upload_img")
    path = os.path.join(settings.MEDIA_ROOT, "add_post_img", img_obj.name)  #上传位置

    with open(path, "wb") as f:     #以二进制格式读取文件
        for line in img_obj:
            f.write(line)

    response = {
        "error": 0,
        "url": "/media/add_post_img/%s" % img_obj.name,
    }

    return HttpResponse(json.dumps(response))       #将json返回页面