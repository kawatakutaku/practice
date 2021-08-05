
@login_required(login_url='/make_trip/')
def edit(request, num):
    trip_model = Trip.objects.get(id=num)
    print('trip_model:', trip_model)
    group_model = Group.objects.get(id=trip_model.group.id)
    print('group_model:', group_model)
    trip = Trip.objects.filter(group=group_model)
    print('trip:',trip)
    if group_model.user == request.user:
        other_model = Other.objects.filter(trip=trip_model.id)
        spot_model = Spot.objects.filter(trip=trip_model)
        spot_first_model = Spot.objects.filter(trip=trip_model).first()
        transport_model = Transport.objects.filter(spot__in=spot_model)
        print('spot_model:', spot_model)

        OtherFormSet = forms.modelformset_factory(
            Other, form=OtherForm, extra=0
        )
        SpotFormSet = forms.modelformset_factory(
            Spot, form=SpotForm, extra=0
        )
        TransportFormSet = forms.modelformset_factory(
            Transport, form=TransportForm, extra=0
        )

        # idがnumのtripを取得する
        if request.method == 'POST':
            print('request.post:', request.POST)
            # 更新時は既に親モデルと繋がっている状態で渡されるから、いちいち外部キーを取得する必要はない
            group = GroupForm(request.POST, instance=group_model)
            trip = TripForm(request.POST, instance=trip_model)
            others = OtherFormSet(request.POST, queryset=other_model)
            spots = SpotFormSet(request.POST, queryset=spot_model)
            spot_first = SpotForm(request.POST, instance=spot_first_model)
            transports = TransportFormSet(request.POST, queryset=transport_model)
            # バリデーションのチェック
            if group.is_valid() and trip.is_valid()and others.is_valid() and spots.is_valid() and spot_first.is_valid() and transports.is_valid():
                group.save()
                trip.save()
                # trip_id = Trip.objects.filter(id=num)
                others.save()
                for other_db in others:
                    other_db.trip = trip_model
                    other_db.save()

                spot_first = spot_first.save()

                spots.save()
                for spot_db in spot:
                    spot_db.trip = trip_model
                    spot_db.save()

                # transport用にspotの情報を取得する
                spot_id = Spot.objects.filter(trip=trip_model)
                print('spot_id:', spot_id)
                transports.save()
                for i in range(len(transport)):
                    transport[i].spot = spot_id[i]
                    transport[i].save()

                return redirect(to='/make_trip/myPage')

        # Getアクセス時の処理
        else:
            group = GroupForm(instance=group_model)
            trip = TripForm(instance=trip_model)
            others = OtherFormSet(queryset=other_model)
            spots = SpotFormSet(queryset=spot_model)[1:]
            transports = TransportFormSet(queryset=transport_model)
            spot_first = SpotForm(instance=spot_first_model)

        # 金額だけを取得する
        spot_cost = Spot.objects.filter(trip=trip_model).values('spot_cost')
        transport_cost = Transport.objects.filter(spot__in=spot_model).values('transport_fee')
        other_cost = Other.objects.filter(trip=trip_model).values('extra_cost')
        # 取得した金額をリストに格納する
        spot_cost_ls = [spot_cost[i]['spot_cost'] for i in range(len(spot_cost))]
        transport_cost_ls = [transport_cost[i]['transport_fee'] for i in range(len(transport_cost))]
        other_cost_ls = [other_cost[i]['extra_cost'] for i in range(len(other_cost))]
        all_cost = sum(spot_cost_ls) + sum(transport_cost_ls) + sum(other_cost_ls)

        params = {
            'group': group,
            'trip': trip,
            'others': others,
            'spots': spots,
            'transports': transports,
            'spot_first': spot_first,
            'id': num,
            'all_money': all_cost
        }
        return render(request, 'make_trip/edit.html', params)

    else:
        return redirect(to='/make_trip/myPage')