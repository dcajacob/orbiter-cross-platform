// Licensed under the MIT License
#include <fontconfig/fontconfig.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static FcPattern *volatile retained;
static void need(int ok) { if(!ok) abort(); }
static FcPattern *make_pattern(void) {
    FcPattern *p=FcPatternCreate();need(p!=NULL);
    for(int i=0;i<40;++i) {
        char key[64],value[64];snprintf(key,sizeof key,"orbiter-owner-key-%02d",i);
        snprintf(value,sizeof value,"orbiter-owner-value-%02d",i);
        need(FcPatternAddString(p,key,(const FcChar8*)value));
    }
    need(FcPatternObjectCount(p)==40);
    for(int i=0;i<40;++i) {
        char key[64],value[64];FcChar8 *actual=NULL;
        snprintf(key,sizeof key,"orbiter-owner-key-%02d",i);
        snprintf(value,sizeof value,"orbiter-owner-value-%02d",i);
        need(FcPatternGetString(p,key,0,&actual)==FcResultMatch && strcmp(value,(char*)actual)==0);
    }
    FcPattern *copy=FcPatternDuplicate(p);need(copy && FcPatternEqual(p,copy));
    FcPatternDestroy(copy);FcPatternReference(p);FcPatternDestroy(p);
    return p;
}
static void *lose_pattern(void *unused) { (void)unused;make_pattern();return NULL; }
int main(int argc,char **argv) {
    if(argc!=2)return 2;
    if(strcmp(argv[1],"lost")==0) {
        pthread_t worker;need(pthread_create(&worker,NULL,lose_pattern,NULL)==0);
        need(pthread_join(worker,NULL)==0);
    } else {
        FcPattern *p=make_pattern();
        if(strcmp(argv[1],"retained")==0)retained=p;
        else if(strcmp(argv[1],"released")==0)FcPatternDestroy(p);
        else return 3;
    }
    printf("ownership control %s completed\n",argv[1]);fflush(stdout);return 0;
}
