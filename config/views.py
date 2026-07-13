from django.shortcuts import render


def home_view(request):
    return render(request, 'home.html')


def board_view(request):
    return render(request, 'board.html')


def about_view(request):
    return render(request, 'about.html')
