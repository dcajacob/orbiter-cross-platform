// Licensed under the MIT License
// Read-only observations of actual GTK returns; no strong object references kept.
#define _GNU_SOURCE
#include <gtk/gtk.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

static FILE* output;
static pthread_once_t initialize_once=PTHREAD_ONCE_INIT;
static unsigned calls;
static void initialize(void) {
    output=fopen("icon-info-lookups.csv","w");
    if(!output)abort();
    fprintf(output,"call,address,reference_count,name,size,scale\n");
}
__attribute__((constructor)) static void process_only(void) {unsetenv("LD_PRELOAD");}
__attribute__((destructor)) static void finish(void) {if(output)fclose(output);}

GtkIconInfo* gtk_icon_theme_lookup_icon_for_scale(GtkIconTheme* theme,const gchar* name,
                                                gint size,gint scale,GtkIconLookupFlags flags) {
    typedef GtkIconInfo* (*Lookup)(GtkIconTheme*,const gchar*,gint,gint,GtkIconLookupFlags);
    // GTK remains in the actual decoration plugin's local loader scope.
    void* library=dlopen("libgtk-3.so.0",RTLD_NOW|RTLD_LOCAL|RTLD_NOLOAD);
    if(!library)abort();
    Lookup original=(Lookup)dlsym(library,"gtk_icon_theme_lookup_icon_for_scale");
    if(!original || original==gtk_icon_theme_lookup_icon_for_scale)abort();
    GtkIconInfo* info=original(theme,name,size,scale,flags);
    pthread_once(&initialize_once,initialize);
    const unsigned call=__atomic_add_fetch(&calls,1,__ATOMIC_RELAXED);
    // GObject's public ref_count is observed while the returned reference is live.
    // Write the address as text; retaining raw pointers would taint leak scanning.
    const unsigned references=info?__atomic_load_n(&((GObject*)info)->ref_count,__ATOMIC_RELAXED):0;
    fprintf(output,"%u,%p,%u,%s,%d,%d\n",call,(void*)info,references,name?name:"",size,scale);
    fflush(output);
    dlclose(library);
    return info;
}
