// Licensed under the MIT License
#include <fontconfig/fontconfig.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const char *format="%{file}|%{index}|%{family}|%{familylang}|%{style}|%{fullname}|%{weight}|%{slant}|%{width}|%{fontversion}|%{lang}|%{charset}|%{variable}|%{color}|%{scalable}|%{fontfeatures}|%{fontvariations}\n";
static void need(int ok) { if(!ok)abort(); }
static int cmp(const void *a,const void *b) {return strcmp(*(char*const*)a,*(char*const*)b);}
static void dump(FcFontSet *set) {
    need(set!=NULL);char **text=calloc(set->nfont,sizeof(char*));need(text!=NULL);
    for(int i=0;i<set->nfont;++i){text[i]=(char*)FcPatternFormat(set->fonts[i],(const FcChar8*)format);need(text[i]!=NULL);}
    qsort(text,set->nfont,sizeof(char*),cmp);printf("fonts=%d\n",set->nfont);
    for(int i=0;i<set->nfont;++i){fputs(text[i],stdout);FcStrFree((FcChar8*)text[i]);}free(text);
}
int main(int argc,char **argv) {
    if(argc==4 && (strcmp(argv[1],"cache")==0 || strcmp(argv[1],"cache-read")==0)) {
        FcConfig *config=FcConfigCreate();need(config && FcConfigParseAndLoad(config,(FcChar8*)argv[3],FcTrue));
        FcCache *cache=FcDirCacheRead((FcChar8*)argv[2],strcmp(argv[1],"cache")==0,config);need(cache!=NULL);
        FcFontSet *fonts=FcCacheCopySet(cache);dump(fonts);FcFontSetDestroy(fonts);
        FcDirCacheUnload(cache);FcConfigDestroy(config);FcFini();fflush(stdout);fputs("data-complete\n",stderr);return 0;
    }
    if(argc!=2 || strcmp(argv[1],"system")!=0)return 2;
    FcConfig *config=FcInitLoadConfigAndFonts();need(config!=NULL);
    FcObjectSet *objects=FcObjectSetBuild(FC_FILE,FC_INDEX,FC_FAMILY,FC_FAMILYLANG,FC_STYLE,FC_FULLNAME,FC_WEIGHT,FC_SLANT,FC_WIDTH,FC_FONTVERSION,FC_LANG,FC_CHARSET,FC_VARIABLE,FC_COLOR,FC_SCALABLE,FC_FONT_FEATURES,FC_FONT_VARIATIONS,NULL);
    FcPattern *all=FcPatternCreate();need(objects && all);
    FcFontSet *set=FcFontList(config,all,objects);dump(set);FcFontSetDestroy(set);FcObjectSetDestroy(objects);FcPatternDestroy(all);
    const char *queries[]={"Sans","Serif","Monospace","sans-serif:weight=bold","DejaVu Sans:size=10","Liberation Serif:style=Italic","Noto Sans CJK JP:lang=ja","emoji","Symbola","FreeSans","Noto Color Emoji","Arial","Times New Roman","sans-serif:size=18:slant=italic"};
    for(unsigned i=0;i<sizeof queries/sizeof queries[0];++i) {
        FcPattern *p=FcNameParse((FcChar8*)queries[i]);need(p && FcConfigSubstitute(config,p,FcMatchPattern));FcDefaultSubstitute(p);
        FcResult result;FcPattern *match=FcFontMatch(config,p,&result);need(match && result==FcResultMatch);
        FcChar8 *text=FcPatternFormat(match,(FcChar8*)format);need(text!=NULL);printf("query=%s\n",queries[i]);fputs((char*)text,stdout);
        FcStrFree(text);FcPatternDestroy(match);FcPatternDestroy(p);
    }
    FcConfigDestroy(config);FcFini();fflush(stdout);fputs("data-complete\n",stderr);return 0;
}
