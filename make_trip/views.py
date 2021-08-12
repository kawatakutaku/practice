from django.http import HttpResponse, HttpResponseServerError
from django.http.response import HttpResponseBadRequest, Http404
from django.shortcuts import render, redirect
from .forms import BudgetForm, MemoForm, SignUp, Login, GroupForm, TripForm, SpotForm, OtherForm, TransportForm, AddGroup
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required
# from django.contrib.auth.models import User
from django.contrib.auth import logout, login, authenticate
from .models import Budget, Spot, Other, Transport, Trip, Member, Group, Memo
from django.db.models import Sum
import datetime
from django import forms
from django.utils.dateparse import parse_datetime
from django.contrib.auth import get_user_model
from django.views import generic
from django.contrib.sites.shortcuts import get_current_site
from django.core.signing import dumps, BadSignature, SignatureExpired, loads
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.timezone import localtime
from django.contrib import messages
from django.views.decorators.csrf import requires_csrf_token
import requests
import json
import traceback

User = get_user_model()

class Login(LoginView):
    form_class = Login
    template_name = 'make_trip/login.html'

class Logout(LoginRequiredMixin, LogoutView):
    template_name = 'make_trip/logout.html'

@login_required(login_url='/make_trip/')
def logout_form(request):

    return render(request, 'make_trip/logout.html')

# 仮登録用のviewを書く
class SignUp(generic.CreateView):
    template_name = 'make_trip/signup.html'
    form_class = SignUp

    # CreateViewクラスのform_validメソッドを上書きしている
    def form_valid(self, form):
        # is_activeのtrueとfalseの切り替えによって仮登録と本登録を切り替えている
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # 本登録用のurlを送付するための処理
        current_site = get_current_site(self.request)   # requestしたサイトのurlの情報を返してくれる
        domain = current_site.domain    # requestしたサイトのdomain情報を返す

        params = {
            'protocol': self.request.scheme,    # schemeでrequestしたサイトのprotocolの情報を教えてくれる(大抵httpかhttps)
            'domain': domain,
            'token': dumps(user.pk),    # userのpkを暗号化してくれる
            'user': user
        }

        # 今回はメールに送るからhttpresponseをする必要はないのでrender_to_stringを使う
        subject = render_to_string('make_trip/mail_template/create/subject.txt', params)    # ここは件名
        message = render_to_string('make_trip/mail_template/create/message.txt', params)    # ここはメールの本文

        user.email_user(subject, message)

        return redirect(to='/make_trip/sign_up_done')

class SignUpDone(generic.TemplateView):
    # 仮登録が完了した時に表示する画面
    template_name = 'make_trip/sign_up_done.html'

class SignUpComplete(generic.TemplateView):
    # 本登録の完了
    template_name = 'make_trip/sign_up_complete.html'
    timeout_seconds = getattr(settings, 'ACTIVATION_TIMEOUT_SECONDS', 60*60*24)

    def get(self, request, **kwargs):
        '''tokenが正しければ本登録'''
        token = kwargs.get('token')

        try:
            user_id = loads(token, max_age=self.timeout_seconds)
        # 期限切れ
        except SignatureExpired:
            return HttpResponseBadRequest()
        # tokenがおかしい
        except BadSignature:
            return HttpResponseBadRequest()

        # tokenには問題ない
        else:
            try:
                user = User.objects.get(pk=user_id)
            # ユーザーが存在しない場合
            except User.DoesNotExist:
                return HttpResponseBadRequest()
            # 問題ない時は本登録する
            else:
                if not user.is_active:
                    user.is_active = True
                    user.save()
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    return super().get(request, **kwargs)

        return HttpResponseBadRequest()

@login_required(login_url='/make_trip/')
def add_member(request, num):
    try:
        this_group = Group.objects.get(id=num)
    except Group.DoesNotExist:
        raise Http404('このグループは存在しません')
    group = Group.objects.filter(id=num).values('title')[0]['title']

    # request.userがグループのメンバーかどうかを判定
    member_exist = Member.objects.filter(group=num).filter(user=request.user)

    if member_exist:
        current_site = get_current_site(request)   # requestしたサイトのurlの情報を返してくれる
        domain = current_site.domain    # requestしたサイトのdomain情報を返す

        params = {
            'protocol': request.scheme,    # schemeでrequestしたサイトのprotocolの情報を教えてくれる(大抵httpかhttps)
            'domain': domain,
            'token': dumps(this_group.pk),    # groupのidを暗号化してくれる
            'group': group,
        }

        return render(request, 'make_trip/add_member.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def add_group(request):
    if request.method == 'POST':
        input_url = AddGroup(request.POST)
        print('input_url:', request.POST['input_url'])
        return redirect(to=request.POST['input_url'])
    else:
        input_url = AddGroup()

    params = {
        'input_url': input_url
    }

    return render(request, 'make_trip/add_group.html', params)

@login_required(login_url='/make_trip/')
def add_member_complete(request, token):
    # 参加させるグループを取得
    try:
        id = loads(token)
        this_group = Group.objects.get(id=id)
    except Group.DoesNotExist:
        raise Http404('このグループは存在しません')
    group = Group.objects.filter(id=id).values('title')[0]['title']

    # グループに所属しているメンバーを取得する
    group_member = Member.objects.filter(group=this_group).values('user')
    member_email = [User.objects.filter(id=group_member[i]['user']).values('email')[0]['email'] for i in range(len(group_member))]

    if request.method == 'POST':
        if str(request.user) in member_email:   # request.userをstr型にしておく必要がある
            messages.info(request, 'すでにメンバーになっています。')
        else:
            member = Member()
            member.user = request.user
            member.group = this_group
            member.save()
            return redirect(to='/make_trip/myPage')
        # login(request, request.user, backend='django.contrib.auth.backends.ModelBackend')

    params = {
        'group': group,
        'token': token,
    }

    return render(request, 'make_trip/add_member_complete.html', params)


# マイページの部分の処理
@login_required(login_url='/make_trip/')
def myPage(request):
    # requestしたユーザーがメンバーとして所属しているグループを取得
    group_member = Member.objects.filter(user=request.user).all().values('group')
    print('group_member:', group_member)

    # 所属しているグループのtrip情報を取得
    groups = Group.objects.filter(id__in=group_member)
    print('groups:', groups)

    # tripの情報があるかチェックする
    # group_exist = Group.objects.filter(user=request.user).count()

    # 次の旅行とこれまでの旅行をまとめるためのリストを作成しておく
    trip_content_before = []
    trip_content_future = []

    # DBにTripの情報が登録されている場合はそのデータを表示する
    if groups:
        trip_content = Trip.objects.all().filter(group__in=groups).values('id', 'trip_name', 'start', 'end')
        trip = Trip.objects.all().filter(group__in=groups)

        # 未来の旅行と過去の旅行に分ける
        for i in range(len(trip_content)):
            # tripがspotを持っていない場合はcontinueする
            spot_exist = Spot.objects.filter(trip=trip_content[i]['id'])
            if spot_exist:
                print('end:', trip_content[i]['end'])
                print('today:', datetime.date.today())
                if trip_content[i]['end'] < datetime.date.today():
                    # 過去の旅行の場合はtrip_content_beforeに格納する
                    trip_content_before.append(trip_content[i])
                else:
                    # 未来の旅行の場合はtrip_content_futureに格納する
                    trip_content_future.append(trip_content[i])
            else:
                # first_spotが登録されていないtripは削除する
                trip[i].delete()

    params = {
        'trip_content_future': trip_content_future,
        'trip_content_before': trip_content_before
    }

    return render(request, 'make_trip/mypage.html', params)

@login_required(login_url='/make_trip/')
def groups(request):
    my_member = Member.objects.filter(user=request.user).values('group')

    # requestしたユーザーがメンバーのグループを取得
    my_group = Group.objects.filter(id__in=my_member)

    # グループに所属しているtripを取得
    trip_contents = Trip.objects.all().filter(group__in=my_group).values('id', 'trip_name', 'start', 'end')
    trips = Trip.objects.all().filter(group__in=my_group)
    for i in range(len(trip_contents)):
        spot = Spot.objects.filter(trip=trip_contents[i]['id'])
        if not spot:
            trips[i].delete()

    if my_group:
        all_group = my_group.values('id', 'title', 'user')
        # グループの作成者のusernameを取得
        group_owners = [User.objects.filter(id=all_group[i]['user']).values('username')[0]['username'] for i in range(len(all_group))]

    else:
        all_group = None
        group_owners = ''

    params = {
        'all_group': all_group,
        'group_owners': group_owners
    }

    return render(request, 'make_trip/groups.html', params)

@login_required(login_url='/make_trip/')
def group_trip(request, num):
    # tripの情報があるかチェックする
    try:
        groups = Group.objects.get(id=num)
    except Group.DoesNotExist:
        raise Http404('このグループは存在しません')

    # グループ内の人数とグループの名前を取得
    member_cnt = Member.objects.filter(group=groups).count()
    group_name = Group.objects.filter(id=num).values('title')[0]['title']

    # request.userがグループのメンバーかどうかを判定
    member_exist = Member.objects.filter(group=num).filter(user=request.user)

    if member_exist:
        # DBにTripの情報が登録されている場合はそのデータを表示する
        if groups:
            # group = Group.objects.all().filter(user=request.user)
            # trip_obj = Trip.objects.filter(group__in=group)
            # print(group)
            trip_content_before = []
            trip_content_future = []
            trip_content = Trip.objects.all().filter(group=groups).values('id', 'trip_name', 'start', 'end')

            # print('trip_content:', trip_content)
            # 未来の旅行と過去の旅行に分ける
            for i in range(len(trip_content)):
                if trip_content[i]['end'] < datetime.date.today():
                    # 過去の旅行の場合はtrip_content_beforeに格納する
                    trip_content_before.append(trip_content[i])
                else:
                    # 未来の旅行の場合はtrip_content_futureに格納する
                    trip_content_future.append(trip_content[i])

        else:
            trip_content_before = []
            trip_content_future = []

        params = {
            'trip_content_future': trip_content_future,
            'trip_content_before': trip_content_before,
            'id': num,
            'member_cnt': member_cnt,
            'group_name': group_name
        }

        return render(request, 'make_trip/group_trip.html', params)
    else:
        return redirect(to='/make_trip/myPage')


@login_required(login_url='/make_trip/')
def members(request, num):
    # 所属しているグループのtrip情報を取得

    # tripの情報があるかチェックする
    try:
        groups = Group.objects.get(id=num)
    except Group.DoesNotExist:
        raise Http404('このグループは存在しません')

    # request.userがグループのメンバーかどうかを判定
    member_exist = Member.objects.filter(group=num).filter(user=request.user)

    if member_exist:
        # グループ内の人数とグループの名前を取得
        members = Member.objects.filter(group=num).values('user', 'id')
        member_username = [User.objects.filter(id=members[i]['user']).values('username')[0]['username'] for i in range(len(members))]
        group_name = Group.objects.filter(id=num).values('title')[0]['title']

        # メンバー全員のIDを取得
        member_id = [members[i]['id'] for i in range(len(members))]

        params = {
            'ids': member_id,
            'members': member_username,
            'group_name': group_name
        }

        return render(request, 'make_trip/members.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def member_delete(request, num):
    # request.userがグループのメンバーかどうかを判定
    member = Member.objects.filter(id=num).first()

    try:
        member = Member.objects.get(id=num)
    except Member.DoesNotExist:
        raise Http404('このメンバーは存在しません')

    request_member = Member.objects.filter(group=member.group.id).filter(user=request.user).first()

    member_info = User.objects.filter(id=member.user.id).values('email', 'username').first()
    if request_member:
        if request.method == 'POST':
            if str(request.user) == member_info['email']:
                messages.info(request, 'ご自身を退会させることはできません')

            else:
                member.delete()

                return redirect(to='/make_trip/members/' + str(member.group.id))

        params = { 'id': num, 'member': member_info }

        return render(request, 'make_trip/member_delete.html', params)

    else:
        return redirect(to='/make_trip/myPage')


@login_required(login_url='/make_trip/')
def delete(request, num):
    # trip_idを元にしてメンバーが所属しているかチェック
    try:
        trip_obj = Trip.objects.get(id=num)
    except Trip.DoesNotExist:
        raise Http404('この旅行は存在しません')
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    # DBにメンバーとしての情報が登録されている場合はそのデータを表示する
    if member_exist:
        if request.method == 'POST':
            trip_obj.delete()
            return redirect(to='/make_trip/myPage')

        params = { 'delete': trip_obj, 'id': num }

        return render(request, 'make_trip/delete.html', params)

    else:
        return redirect(to='/make_trip/myPage')



@login_required(login_url='/make_trip/')
def create_trip(request):
    # views側でもエラーの時にセッションを残すようにしておく
    group = GroupForm(request.POST or None)
    trip = TripForm(request.POST or None)
    budget = BudgetForm(request.POST or None)
    member = Member()

    # エラーメッセージを作成しておく(デフォルトでは何もなし)
    error_msg_start = ''
    error_msg_end = ''

    params = { 'group': group, 'trip': trip, 'budget': budget, 'error_msg_start': error_msg_start, 'error_msg_end': error_msg_end }


    if request.method == 'POST' and group.is_valid() and trip.is_valid() and budget.is_valid():
        start = request.POST['start']
        end = request.POST['end']
        # end+1日しておくことでendの日も入力することができる
        # end = datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(days=1)
        today = datetime.datetime.today()
        yesterday = today - datetime.timedelta(days=1)

        if not str(yesterday) <= start:
            # startが今日より前の日の場合のエラーメッセージ
            error_msg_start = '今日の日付よりも後の日付を入力してください'
            params['error_msg_start'] = error_msg_start
        elif not start <= str(end):
            error_msg_end = '出発日以降の日付を入力してください'
            params['error_msg_end'] = error_msg_end
        else:
            try:
                request.session['form_data']
                del request.session['form_data']
            except:
                print('セッションOKです')
            # まずはグループ名を保存
            group_db = group.save(commit=False)
            group_db.user = request.user
            group_db.save()

            # trip_titleの情報を保存
            group_id = Group.objects.filter(user=request.user).order_by('-id').first()
            trip_db = trip.save(commit=False)
            trip_db.group = group_id
            trip_db.save()

            # budgetの情報を保存する
            trip_id = Trip.objects.filter(group=group_id).order_by('-id').first()
            budget_db = budget.save(commit=False)
            budget_db.trip = trip_id
            budget_db.save()

            # 作成したグループのメンバーとしてグループ作成者を登録
            member.user = request.user
            member.group = group_id
            member.save()

            # trip_idの情報を保存
            return redirect(to='/make_trip/first_spot')

    return render(request, 'make_trip/create_trip.html', params)

@login_required(login_url='/make_trip/')
def first_spot(request):
    spot = SpotForm(request.POST or None)

    # tripからstartとendの情報を取得する
    group_id = Group.objects.filter(user=request.user).order_by('-id').first()
    trip = Trip.objects.filter(group=group_id).order_by('-id').values('start', 'end', 'id').first()
    start = trip['start']
    end = trip['end']
    budget = Budget.objects.filter(trip=trip['id']).first()
    print('budget')

    # エラーメッセージを作成しておく(デフォルトでは何もなし)
    error_msg_spot_1 = ''
    error_msg_spot_2 = ''

    params = { 'trip': trip, 'spot': spot, 'start': start, 'end': end, 'error_msg_spot_1': error_msg_spot_1, 'error_msg_spot_2': error_msg_spot_2}

    # end+1日しておくことでendの日も入力することができる
    end_time = end + datetime.timedelta(days=1)
    start_time = start

    if request.method == 'POST' and spot.is_valid():
        spot_time = request.POST['spot_time']

        if not str(start_time) <= spot_time:
            # 最初のspotの到着時間がstartよりも前の日付の場合のエラーメッセージ
            error_msg_spot_1 = '出発日以降の日付を入力してください'
            params['error_msg_spot_1'] = error_msg_spot_1
        elif not spot_time <= str(end_time):
            error_msg_spot_2 = '帰宅日以前の日付を入力してください'
            params['error_msg_spot_2'] = error_msg_spot_2
        else:
            try:
                request.session['form_data']
                del request.session['form_data']
            except:
                print('セッションOKです')

            # spotの情報を保存
            trip_id = Trip.objects.filter(group=group_id).order_by('-id').first()
            spot_db = spot.save(commit=False)
            spot_db.trip = trip_id
            spot_db.save()

            return redirect(to='/make_trip/trip/' + str(trip_id.id))

    return render(request, 'make_trip/first_spot.html', params)


@login_required(login_url='/make_trip/')
def create_this_group_trip(request, num):
    # views側でもエラーの時にセッションを残すようにしておく
    trip = TripForm(request.POST or None)
    budget = BudgetForm(request.POST or None)

    # エラーメッセージを作成しておく(デフォルトでは何もなし)
    error_msg_start = ''
    error_msg_end = ''

    # グループ名を取得
    try:
        this_group = Group.objects.get(id=num)
    except Group.DoesNotExist:
        raise Http404('このグループは存在しません')
    group_name = Group.objects.filter(id=num).values('title')[0]['title']
    member_cnt = Member.objects.filter(group=num).count()

    # request.userがグループのメンバーかどうかを判定
    member_exist = Member.objects.filter(group=num).filter(user=request.user)

    if member_exist:
        params = { 'trip': trip, 'budget': budget, 'error_msg_start': error_msg_start, 'error_msg_end': error_msg_end, 'id': num, 'group_name': group_name, 'member_cnt': member_cnt}

        if request.method == 'POST' and trip.is_valid():
            start = request.POST['start']
            end = request.POST['end']
            # end+1日しておくことでendの日も入力することができる
            end = datetime.datetime.strptime(end, '%Y-%m-%d') + datetime.timedelta(days=1)
            today = datetime.datetime.today()
            yesterday = today - datetime.timedelta(days=1)

            if not str(yesterday) <= start:
                # startが今日より前の日の場合のエラーメッセージ
                error_msg_start = '今日の日付以降の日付を入力してください'
                params['error_msg_start'] = error_msg_start
            elif not start <= str(end):
                error_msg_end = '出発日以降の日付を入力してください'
                params['error_msg_end'] = error_msg_end
            else:
                try:
                    request.session['form_data']
                    del request.session['form_data']
                except:
                    print('セッションOKです')
                # trip_titleの情報を保存
                group_id = Group.objects.get(id=num)
                trip_db = trip.save(commit=False)
                trip_db.group = group_id
                trip_db.save()

                # budgetの情報を保存する
                trip_id = Trip.objects.filter(group=group_id).order_by('-id').first()
                budget_db = budget.save(commit=False)
                budget_db.trip = trip_id
                budget_db.save()

                return redirect(to='/make_trip/group_trip_first_spot/' + str(num))

        return render(request, 'make_trip/create_this_group_trip.html', params)

    else:
        return redirect(to='/make_trip/myPage')



@login_required(login_url='/make_trip/')
def group_trip_first_spot(request, num):
    spot = SpotForm(request.POST or None)

    try:
        this_group = Group.objects.get(id=num)
    except Group.DoesNotExist:
        raise Http404('このグループは存在しません')

    # request.userがグループのメンバーかどうかを判定
    member_exist = Member.objects.filter(group=num).filter(user=request.user)

    if member_exist:
        # tripからstartとendの情報を取得する
        group_id = Group.objects.filter(id=num).first()

        trip = Trip.objects.filter(group=group_id).order_by('-id').values('start', 'end').first()
        start = trip['start']
        end = trip['end']

        # エラーメッセージを作成しておく(デフォルトでは何もなし)
        error_msg_spot_1 = ''
        error_msg_spot_2 = ''

        params = { 'trip': trip, 'spot': spot, 'start': start, 'end': end, 'error_msg_spot_1': error_msg_spot_1, 'error_msg_spot_2': error_msg_spot_2, 'id': num}

        # end+1日しておくことでendの日も入力することができる
        end_time = end + datetime.timedelta(days=1)
        start_time = start

        if request.method == 'POST' and spot.is_valid():
            spot_time = request.POST['spot_time']

            if not str(start_time) <= spot_time:
                # 最初のspotの到着時間がstartよりも前の日付の場合のエラーメッセージ
                error_msg_spot_1 = '出発日以降の日付を入力してください'
                params['error_msg_spot_1'] = error_msg_spot_1
            elif not spot_time <= str(end_time):
                error_msg_spot_2 = '帰宅日以前の日付を入力してください'
                params['error_msg_spot_2'] = error_msg_spot_2
            else:
                try:
                    request.session['form_data']
                    del request.session['form_data']
                except:
                    print('セッションOKです')

                # spotの情報を保存
                trip_id = Trip.objects.filter(group=group_id).order_by('-id').first()
                spot_db = spot.save(commit=False)
                spot_db.trip = trip_id
                spot_db.save()

                return redirect(to='/make_trip/trip/' + str(trip_id.id))

        return render(request, 'make_trip/group_trip_first_spot.html', params)

    else:
        return redirect(to='/make_trip/myPage')


@login_required(login_url='/make_trip/')
def other(request, num):
    other = OtherForm(request.POST or None)

    # 上で取得したtrip_idを持つgroupに所属しているかチェック
    # request.userがグループのメンバーかどうかを判定
    try:
        trip_obj = Trip.objects.get(id=num)
    except Trip.DoesNotExist:
        raise Http404('この旅行は存在しません')
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist:
        others = Other.objects.filter(trip=trip_obj)

        # 費用の計算
        other_cost = Other.objects.filter(trip=trip_obj).values('extra_cost')
        other_cost_ls = [other_cost[i]['extra_cost'] for i in range(len(other_cost))]
        costs = sum(other_cost_ls)

        if other.is_valid():
            other_db = other.save(commit=False)
            other_db.trip = trip_obj
            other_db.save()

            return redirect(to='/make_trip/trip/' + str(num))

        params = { 'other': other, 'id': num, 'others': others, 'other_cost': costs }

        return render(request, 'make_trip/other.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def trip(request, num):
    try:
        trip = Trip.objects.get(id=num)
    except Trip.DoesNotExist:
        raise Http404('この旅行は存在しません')
    group_id = Group.objects.filter(id=trip.group.id).values('id')[0]['id']

    # request.userがグループのメンバーかどうかを判定
    member_exist = Member.objects.filter(group=group_id).filter(user=request.user)

    if member_exist:
        spots = Spot.objects.filter(trip=trip)
        others = Other.objects.filter(trip=trip)
        transports = Transport.objects.filter(spot__in=spots)
        group_name = Group.objects.filter(id=trip.group.id).values('title')[0]['title']
        member_cnt = Member.objects.filter(group=trip.group.id).count()
        # メモの情報をDBから取得しておく
        memo_exist = Memo.objects.filter(trip=trip)
        if memo_exist:
            memo_db = Memo.objects.get(trip=trip)
            memo = MemoForm(request.POST or None, instance=memo_db)
        else:
            memo = MemoForm(request.POST or None)

        # 金額だけを取得する
        spot_cost = Spot.objects.filter(trip=trip).values('spot_cost')
        transport_cost = Transport.objects.filter(spot__in=spots).values('transport_fee')
        other_cost = Other.objects.filter(trip=trip).values('extra_cost')
        # 取得した金額をリストに格納する
        spot_cost_ls = [spot_cost[i]['spot_cost'] for i in range(len(spot_cost))]
        transport_cost_ls = [transport_cost[i]['transport_fee'] for i in range(len(transport_cost))]
        other_cost_ls = [other_cost[i]['extra_cost'] for i in range(len(other_cost))]
        each_money = sum(spot_cost_ls) + sum(transport_cost_ls) + sum(other_cost_ls)
        all_money = each_money * member_cnt

        # 予算を取得
        budget = Budget.objects.filter(trip=trip).values('predict_money').first()['predict_money']
        print('budget:', budget)

        rest_money = budget - each_money

        params = {
            'trip': trip,
            'spots': spots[1:],
            'others': others,
            'transports': transports,
            'each_money': each_money,
            'all_money': all_money,
            'spot_first': spots[0],
            'id': num,
            'group_name': group_name,
            'member_cnt': member_cnt,
            'group_id': group_id,
            'memo': memo,
            'budget': budget,
            'rest_money': rest_money
        }

        if request.method == 'POST' and memo.is_valid():
            # memoの情報を保存する
            memo_db = memo.save(commit=False)
            memo_db.trip = trip
            memo_db.save()

        return render(request, 'make_trip/trip.html', params)

    else:
        return redirect(to='/make_trip/myPage')


@login_required(login_url='/make_trip/')
def trip_edit(request, num):
    try:
        trip_obj = Trip.objects.get(id=num)
    except Trip.DoesNotExist:
        raise Http404('この旅行は存在しません')
    trip = TripForm(request.POST or None, instance=trip_obj)


    # request.userがグループのメンバーかどうかを判定
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist:
        # エラーメッセージ
        error_before = ''
        error_after = ''

        # startとendの情報を取得
        trip_content = Trip.objects.filter(id=num).values('start', 'end').first()
        start = trip_content['start']
        end = trip_content['end']

        params = { 'id': num, 'trip': trip, 'error_before': error_before, 'error_after': error_after, 'start': start, 'end': end}

        if request.method == 'POST' and trip.is_valid():
            start = request.POST['start']
            end = request.POST['end']
            today = datetime.datetime.today()
            yesterday = today - datetime.timedelta(days=1)
            if not str(yesterday) <= start:
                params['error_before'] = str(today) + 'よりも後の日時を入力してください'
            elif not start <= end:
                params['error_after'] = start + 'よりも後の日時を入力してください'
                # request.session['session_data'] = request.POST
                # return redirect(to='/make_trip/trip_edit/' + str(num))
            else:
                try:
                    request.session['session_data']
                    del request.session['session_data']
                except:
                    print('セッションOKです')
                trip.save()
                return redirect(to='/make_trip/trip/' + str(num))

        return render(request, 'make_trip/trip_edit.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def spot_edit(request, num):
    try:
        spot_db = Spot.objects.get(id=num)
    except Spot.DoesNotExist:
        raise Http404('この観光地は存在しません')
    spot = SpotForm(request.POST or None, instance=spot_db)

    # このspotが属しているtripのidを取得している
    trip_id = spot_db.trip.id

    # 上で取得したtrip_idを持つgroupに所属しているかチェック
    # request.userがグループのメンバーかどうかを判定
    trip_obj = Trip.objects.get(id=trip_id)
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist:
        # このspotの前後にspotがあるかどうかを判定する => 前にない(先頭)ならstartと比較 => 後にない(最後尾)ならendと比較
        all_spot = Spot.objects.filter(trip=trip_id).values('id')
        for i in range(len(all_spot)):
            if all_spot[i]['id'] == num:
                index = i
                break

        # jsに渡すためにstartとendのデータを取得しておく
        start = Trip.objects.filter(id=trip_id).values('start')[0]['start']
        end = Trip.objects.filter(id=trip_id).values('end')[0]['end']

        # index+1が存在するかどうかをチェックする
        # 存在するなら、次の観光地のidをfkに持つtransportの日付を取得
        # 前後のtransportがあればそれを使用し、無いなら、Tripのstartとendを使用する
        if index == 0 and not len(all_spot) == index+1:
            before_time = None
            # spot_dbの次のspotのidを取得する
            spot_id = Spot.objects.get(id=all_spot[index+1]['id'])
            after_time = Transport.objects.filter(spot=spot_id).values('transport_time')[0]['transport_time']
            after_time = localtime(after_time)
        elif index != 0 and len(all_spot) == index+1:
            before_time = Transport.objects.filter(spot=spot_db).values('transport_time')[0]['transport_time']
            before_time = localtime(before_time)
            after_time = None
        elif index == 0 and len(all_spot) == index+1:
            before_time = None
            after_time = None
        else:
            before_time = Transport.objects.filter(spot=spot_db).values('transport_time')[0]['transport_time']
            after_time = Transport.objects.filter(spot=all_spot[index+1]['id']).values('transport_time')[0]['transport_time']
            # このままだと標準時の時刻が出てくるからlocaltimeで日本に合わせる
            before_time = localtime(before_time)
            after_time = localtime(after_time)

        # エラーメッセージを格納しておく
        error_before = ''
        error_after = ''

        params = {
            'id': num,
            'spot': spot,
            'start': start,
            'end': end,
            'before_time': before_time,
            'after_time': after_time,
            'error_before': error_before,
            'error_after': error_after
        }

        # 最終日を+1日しておくことで最終日の日程も入力することができる
        end_time = end + datetime.timedelta(days=1)
        start_time = start

        # Post送信時の処理
        if request.method == 'POST' and spot.is_valid():
            spot_time = request.POST['spot_time']
            if before_time != None and not str(before_time) <= spot_time:
                params['error_before'] = str(before_time) + 'よりも後の日時を入力してください'
            elif after_time != None and not spot_time <= str(after_time):
                params['error_after'] = str(after_time) + 'よりも前の日時を入力してください'
                # return redirect(to='/make_trip/spot_edit/' + str(num))
            elif before_time == None and not str(start_time) <= spot_time:
                params['error_before'] = str(start_time) + 'よりも後の日時を入力してください'
            elif after_time == None and not str(end_time) >= spot_time:
                params['error_after'] = str(end) + 'よりも前の日時を入力してください'
            else:
                spot.save()
                return redirect(to='/make_trip/trip/'+ str(trip_id))


        return render(request, 'make_trip/spot_edit.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def transport_edit(request, num):
    try:
        transport_db = Transport.objects.get(id=num)
    except Transport.DoesNotExist:
        raise Http404('この移動手段は存在しません')
    transport = TransportForm(request.POST or None, instance=transport_db)

    # このtransportが属しているtripのidを取得している
    spot_id = transport_db.spot.id
    # spotを元にしてtripのidを取得する
    spot = Spot.objects.get(id=spot_id)
    trip_id = spot.trip.id

    # 上で取得したtrip_idを持つgroupに所属しているかチェック
    # request.userがグループのメンバーかどうかを判定
    trip_obj = Trip.objects.get(id=trip_id)
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist:
        # この旅行の全てのspotを取得する
        all_spot = Spot.objects.filter(trip=trip_id).values('id')
        # 取得したspotのidの中からtransportとセットになっているspotのidを探す
        for i in range(len(all_spot)):
            if all_spot[i]['id'] == spot_id:
                index = i
                break
        # spotのidのインデックスを取得して、それより一つ前のspotを取得する
        before_spot = all_spot[index-1]['id']
        before_time = Spot.objects.filter(id=before_spot).values('spot_time')[0]['spot_time']
        # 1つ後ろのspotの時間を取得する
        after_time = Spot.objects.filter(id=spot_id).values(('spot_time'))[0]['spot_time']

        local_before_time = localtime(before_time)
        local_after_time = localtime(after_time)

        # エラーメッセージ
        error_before = ''
        error_after = ''

        params = {
            'id': num,
            'transport': transport,
            'before_time': before_time,
            'after_time': after_time,
            'error_before': error_before,
            'error_after': error_after
        }

        if request.method == 'POST' and transport.is_valid():
            transport_time = request.POST['transport_time']
            if not str(local_before_time) <= transport_time:
                params['error_before'] = str(local_before_time) + 'よりも後の日時を入力してください'
            elif not transport_time <= str(local_after_time):
                params['error_after'] = str(local_after_time) + 'よりも前の日時を入力してください'
                # return redirect(to='/make_trip/transport_edit/' + str(num))
            else:
                transport.save()
                return redirect(to='/make_trip/trip/' + str(trip_id))


        return render(request, 'make_trip/transport_edit.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def other_edit(request, num):
    try:
        other_db = Other.objects.get(id=num)
    except Other.DoesNotExist:
        raise Http404('この費用は存在しません')
    other = OtherForm(request.POST or None, instance=other_db)

    # このotherが属しているtripのidを取得している
    trip_id = other_db.trip.id

    # 上で取得したtrip_idを持つgroupに所属しているかチェック
    # request.userがグループのメンバーかどうかを判定
    trip_obj = Trip.objects.get(id=trip_id)
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist:
        if request.method == 'POST' and other.is_valid():
            other.save()
            return redirect(to='/make_trip/trip/' + str(trip_id))

        params = {
            'id': num,
            'other': other
        }

        return render(request, 'make_trip/other_edit.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def spot_delete(request, num):
    try:
        spot = Spot.objects.get(id=num)
    except Spot.DoesNotExist:
        raise Http404('この観光地は存在しません')

    # このspotと紐づいたtransportを取得
    transport = Transport.objects.get(spot=spot.id)

    # このspotが属しているtripのidを取得している
    trip_id = spot.trip.id
    # 上で取得したtrip_idを持つgroupに所属しているかチェック
    # request.userがグループのメンバーかどうかを判定
    trip_obj = Trip.objects.get(id=trip_id)
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist:
        if request.method == 'POST':
            # その観光地を削除する
            spot.delete()

            return redirect(to='/make_trip/trip/'+ str(trip_id))

        params = {
            'id': num,
            'spot': spot,
            'transport': transport
        }

        return render(request, 'make_trip/spot_delete.html', params)

    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def other_delete(request, num):
    try:
        other_db = Other.objects.get(id=num)
    except Other.DoesNotExist:
        raise Http404('この費用は存在しません')

    # このotherが属しているtripのidを取得している
    trip_id = other_db.trip.id
    # 上で取得したtrip_idを持つgroupに所属しているかチェック
    # request.userがグループのメンバーかどうかを判定
    trip_obj = Trip.objects.get(id=trip_id)
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist and other_db:
        other_db.delete()

        return redirect(to='/make_trip/trip/' + str(trip_id))
    else:
        return redirect(to='/make_trip/myPage')

@login_required(login_url='/make_trip/')
def group_remove(request, num):
    try:
        this_group = Group.objects.get(id=num)
    except Group.DoesNotExist:
        raise Http404('このグループは存在しません')

    # request.userがグループのメンバーかどうかを判定
    member = Member.objects.filter(group=num).filter(user=request.user).first()
    if member:
        group_name = Group.objects.filter(id=num).values('title')[0]['title']
        username = User.objects.filter(id=this_group.user.id).values('username')[0]['username']

        if member:
            if request.method == 'POST':
                member.delete()

                # グループ内にメンバーが1人もいない場合はグループも消す
                member_exist = Member.objects.filter(group=num).count()
                if member_exist == 0:
                    this_group.delete()

                return redirect(to='/make_trip/groups')
        else:
            return redirect(to='/make_trip/myPage')

        params = { 'id': num, 'group_name': group_name, 'username': username }

        return render(request, 'make_trip/group_remove.html', params)

    else:
        return redirect(to='/make_trip/myPage')


@login_required(login_url='/make_trip/')
def tranSpot(request, num):
    spot = SpotForm(request.POST or None)
    transport = TransportForm(request.POST or None)

    # request.userがグループのメンバーかどうかを判定
    try:
        trip_obj = Trip.objects.get(id=num)
    except Trip.DoesNotExist:
        raise Http404('この旅行は存在しません')
    member_exist = Member.objects.filter(group=trip_obj.group.id).filter(user=request.user)   # tripのobjectの中にgroupのidも入っているからそれをmemberにも使う

    if member_exist:
        spots = Spot.objects.filter(trip=num)
        transports = Transport.objects.filter(spot__in=spots)

        # 費用の計算
        spot_cost = Spot.objects.filter(trip=num).values('spot_cost')
        transport_cost = Transport.objects.filter(spot__in=spots).values('transport_fee')
        spot_cost_ls = [spot_cost[i]['spot_cost'] for i in range(len(spot_cost))]
        transport_cost_ls = [transport_cost[i]['transport_fee'] for i in range(len(transport_cost))]

        costs = sum(spot_cost_ls) + sum(transport_cost_ls)

        # startとendと最初のspotの時間を取得
        trip = Trip.objects.filter(id=num).values('end')
        before_time = Spot.objects.filter(trip=num).order_by('-id').values('spot_time')[0]['spot_time']
        end = trip[0]['end']
        before_time = localtime(before_time)

        # エラーメッセージ
        error_before = ''
        error_after = ''
        error_early_spot = ''

        # renderingの際に用いるparameter達
        params = { 'spot': spot, 'transport': transport, 'id': num, 'first_spot': spots[0], 'spots': spots[1:], 'transports': transports,
                'costs': costs, 'end': end, 'before_time': before_time,
                'error_before': error_before, 'error_after': error_after, 'error_early_spot': error_early_spot}

        # 最終日を+1日しておくことで最終日の日程も入力できる
        end_time = end + datetime.timedelta(days=1)
        before_time = before_time

        # post送信時
        if request.method == 'POST' and spot.is_valid() and transport.is_valid():
            spot_time = request.POST['spot_time']
            transport_time = request.POST['transport_time']

            # request.session['tranSpot'] = request.POST
            if not str(before_time) <= transport_time:
                params['error_before'] = str(before_time) + 'よりも後の日時を入力してください'
            elif not transport_time <= spot_time:
                params['error_early_spot'] = transport_time + 'よりも後の日時を入力してください'
            elif not spot_time <= str(end_time):
                params['error_after'] = str(end) + 'よりも前の日時を入力してください'
                # return redirect(to='/make_trip/tranSpot/' + str(num))
            else:
                try:
                    request.session['tranSpot']
                    del request.session['tranSpot']
                except:
                    print('セッションOKです')
                spot_db = spot.save(commit=False)
                spot_db.trip = Trip.objects.get(id=num)
                spot_db.save()

                spot_id = Spot.objects.filter().order_by('-id').first()
                transport_db = transport.save(commit=False)
                transport_db.spot = spot_id
                transport_db.save()

                return redirect(to='/make_trip/trip/' + str(num))


        return render(request, 'make_trip/addSpot.html', params)

    else:
        return redirect(to='/make_trip/myPage')


@requires_csrf_token
def my_customized_server_error(request, template_name='500.html'):
    requests.post(
        'https://hooks.slack.com/services/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',
        data=json.dumps({
            'text': '\n'.join([
                f'Request uri: {request.build_absolute_uri()}',
                traceback.format_exc(),
            ]),
            'username': 'Django エラー通知',
            'icon_emoji': ':jack_o_lantern:',
        })
    )
    return HttpResponseServerError('<h1>Server Error (500)だよー</h1>')