// Licensed under the MIT License
#define _GNU_SOURCE
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct _GdkDisplay GdkDisplay;
extern void gdk_set_allowed_backends(const char *backends);
extern GdkDisplay *gdk_display_open(const char *display_name);
static void need(int valid) {if(!valid)abort();}
static void *lose(void *unused) {
    (void)unused;void *p=malloc(73);need(p!=NULL);
    memset(p,23,73);__asm__ __volatile__("" : : "g"(p) : "memory");return NULL;
}
int main(int argc,char **argv) {
    if(argc!=2)return 2;int count=20;
    if(strcmp(argv[1],"once")==0)count=1;
    else if(strcmp(argv[1],"repeat")==0){}
    else if(strcmp(argv[1],"lost")==0){}
    else if(strcmp(argv[1],"borrowed-default")==0) {
        need(setenv("GDK_BACKEND","orbiter-unavailable-test-backend",1)==0);
        need(gdk_display_open(NULL)==NULL);
    } else return 3;
    for(int i=0;i<count;++i) {
        char *owned=malloc(8);need(owned!=NULL);memcpy(owned,"wayland",8);
        gdk_set_allowed_backends(owned);memset(owned,0,8);free(owned);
    }
    if(strcmp(argv[1],"lost")==0){pthread_t thread;need(pthread_create(&thread,NULL,lose,NULL)==0);need(pthread_join(thread,NULL)==0);}
    Dl_info info;need(dladdr((void*)gdk_set_allowed_backends,&info)!=0);
    printf("library=%s\nmode=%s\ncalls=%d\n",info.dli_fname,argv[1],count);fflush(stdout);return 0;
}
