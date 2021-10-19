from django.shortcuts import render, redirect
from . models import Hashtag


def hashtagsEditor(request):
    hashtags = Hashtag.objects.all()

    if request.method == 'POST':
        name = request.POST.get("name")
        instance = Hashtag(name=name)
        instance.save()

        return redirect('/')

    elif request.method == 'GET':
        hashtag_id = request.GET.get("hashtag_id")
        enabled = request.GET.get("enabled")

        if hashtag_id and enabled:
            instance = Hashtag.objects.get(id=hashtag_id)
            if enabled.lower() == "true":
                instance.enabled = True
            else:
                instance.enabled = False

            instance.save()

            return redirect('/')

    context = {"hashtags": hashtags}

    return render(request, 'index.html', context)
