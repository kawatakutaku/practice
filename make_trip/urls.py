from django.urls import path
from . import  views

urlpatterns = [
    path('trip/<int:num>', views.trip, name="trip"),
    path('members/<int:num>', views.members, name="members"),
    path('myPage', views.myPage, name="myPage"),
    path('groups', views.groups, name="groups"),
    path('group_trip/<int:num>', views.group_trip, name="group_trip"),
    path('delete/<int:num>', views.delete, name="delete"),
    path('other/<int:num>', views.other, name="other"),
    path('create_trip', views.create_trip, name="create_trip"),
    path('create_this_group_trip/<int:num>', views.create_this_group_trip, name="create_this_group_trip"),
    path('first_spot', views.first_spot, name="first_spot"),
    path('group_trip_first_spot/<int:num>', views.group_trip_first_spot, name="group_trip_first_spot"),
    path('trip_edit/<int:num>', views.trip_edit, name="trip_edit"),
    path('spot_edit/<int:num>', views.spot_edit, name="spot_edit"),
    path('transport_edit/<int:num>', views.transport_edit, name="transport_edit"),
    path('other_edit/<int:num>', views.other_edit, name="other_edit"),
    path('spot_delete/<int:num>', views.spot_delete, name="spot_delete"),
    path('other_delete/<int:num>', views.other_delete, name="other_delete"),
    path('group_remove/<int:num>', views.group_remove, name="group_remove"),
    path('member_delete/<int:num>', views.member_delete, name="member_delete"),
    path('tranSpot/<int:num>', views.tranSpot, name="tranSpot"),
    path('add_member/<int:num>', views.add_member, name="add_member"),
    path('add_member_complete/<token>', views.add_member_complete, name="add_member_complete"),
    path('add_group', views.add_group, name="add_group"),
]
