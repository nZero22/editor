from django.views import generic
from django.db.models.query import EmptyQuerySet
from django.core.urlresolvers import reverse,reverse_lazy
from django.forms.models import inlineformset_factory
from django.shortcuts import redirect
from django import http
from django.core.exceptions import PermissionDenied

from editor.models import Project, ProjectAccess
import editor.forms
import editor.views.editoritem

class MustBeOwnerMixin(object):
    def dispatch(self,request,*args,**kwargs):
        if request.user != self.get_object().owner:
            raise PermissionDenied
        return super(MustBeOwnerMixin,self).dispatch(request,*args,**kwargs)

class ProjectContextMixin(object):
    model = Project
    context_object_name = 'project'

    def get_context_data(self,**kwargs):
        context = super(ProjectContextMixin,self).get_context_data(**kwargs)
        context['in_project'] = self.get_object()
        context['project_editable'] = self.get_object().can_be_edited_by(self.request.user)
        return context

class SettingsPageMixin(object):
    def get_context_data(self,**kwargs):
        context = super(SettingsPageMixin,self).get_context_data(**kwargs)
        context['settings_page'] = self.settings_page
        return context

class CreateView(generic.CreateView):
    model = Project
    template_name = 'project/create.html'
    fields = ('name','description','default_licence','default_locale')
    
    def form_valid(self,form):
        form.instance.owner = self.request.user
        return super(CreateView,self).form_valid(form)

class DeleteView(ProjectContextMixin,MustBeOwnerMixin,generic.DeleteView):
    template_name = 'project/delete.html'
    success_url = reverse_lazy('editor_index')


class IndexView(ProjectContextMixin,generic.DetailView):
    template_name = 'project/index.html'

class OptionsView(ProjectContextMixin,SettingsPageMixin,generic.UpdateView):
    template_name = 'project/options.html'
    fields = ('name','description','default_locale','default_licence')
    settings_page = 'options'

    def get_success_url(self):
        return reverse('project_settings_options',args=(self.get_object().pk,))

class ManageMembersView(ProjectContextMixin,SettingsPageMixin,generic.UpdateView):
    template_name = 'project/manage_members.html'
    settings_page = 'members'
    form_class = editor.forms.ProjectAccessFormset

    def get_context_data(self,**kwargs):
        context = super(ManageMembersView,self).get_context_data(**kwargs)
        context['add_member_form'] = editor.forms.AddMemberForm({'project':self.object.pk})
        return context

    def post(self,request,*args,**kwargs):
        print("POST")
        return super(ManageMembersView,self).post(request,*args,**kwargs)


    def form_invalid(self, form):
        print("INVALID")
        print(form)
        return super(ManageMembersView,self).form_invalid(form)

    def form_valid(self, form):
        print(form)
        return super(ManageMembersView,self).form_valid(form)

    def get_success_url(self):
        return reverse('project_settings_members',args=(self.get_object().pk,))

class AddMemberView(generic.CreateView):
    model = ProjectAccess
    form_class = editor.forms.AddMemberForm
    template_name = 'project/add_member.html'

    def get_success_url(self):
        return reverse('project_settings_members',args=(self.object.project.pk,))

    def form_invalid(self,form):
        project = form.cleaned_data['project']
        return redirect(reverse('project_settings_members',args=(project.pk,)))

class TransferOwnershipView(ProjectContextMixin,MustBeOwnerMixin,generic.UpdateView):
    template_name = 'project/transfer_ownership.html'
    form_class = editor.forms.TransferOwnershipForm

    def get_success_url(self):
        return reverse('project_settings_members',args=(self.object.pk,))

    def form_valid(self, form):
        project = self.get_object()
        new_owner = form.instance.owner
        if new_owner != project.owner:
            ProjectAccess.objects.filter(project=project,user=new_owner).delete()
            ProjectAccess.objects.create(project=project,user=project.owner,access='edit')
        
        return super(TransferOwnershipView,self).form_valid(form)

class SearchView(editor.views.editoritem.SearchView):
    template_name = 'project/search.html'
    def dispatch(self,request,pk,*args,**kwargs):
        self.project = Project.objects.get(pk=pk)
        return super(SearchView,self).dispatch(request,pk,*args,**kwargs)

    def base_queryset(self):
        return self.project.items.all()

    def get_context_data(self,**kwargs):
        context = super(SearchView,self).get_context_data(**kwargs)
        context['in_project'] = True
        context['project'] = self.project
        return context

class CommentView(editor.views.generic.CommentView):
    model = Project

    def get_comment_object(self):
        return self.get_object()
