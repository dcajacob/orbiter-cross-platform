// Licensed under the MIT License
// Test-only Weston 14 input backend. Never install this module or load it in
// the user's compositor. Commands arrive through a socketpair inherited from
// the owning test harness; application ownership is checked with Wayland peer
// credentials before focus, pointer or keyboard events are delivered.
#define _GNU_SOURCE
#include <libweston/libweston.h>
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
#include <fcntl.h>

// The following exported backend ABI is pinned to Weston 14.0.2. Declarations
// match libweston-internal.h and backend.h in the verified source archive.
void weston_seat_init(struct weston_seat*,struct weston_compositor*,const char*);
void weston_seat_release(struct weston_seat*);
int weston_seat_init_pointer(struct weston_seat*);
int weston_seat_init_keyboard(struct weston_seat*,struct xkb_keymap*);
void notify_motion(struct weston_seat*,const struct timespec*,struct weston_pointer_motion_event*);
void notify_button(struct weston_seat*,const struct timespec*,int32_t,enum wl_pointer_button_state);
void notify_key(struct weston_seat*,const struct timespec*,uint32_t,enum wl_keyboard_key_state,enum weston_key_state_update);
void notify_axis(struct weston_seat*,const struct timespec*,struct weston_pointer_axis_event*);
void notify_axis_source(struct weston_seat*,uint32_t);
void notify_pointer_frame(struct weston_seat*);

struct fixture {
    struct weston_compositor* compositor;
    struct weston_seat seat;
    struct wl_listener destroy;
    struct wl_event_source* source;
    int fd;
};

static pid_t surface_pid(struct weston_surface* surface) {
    pid_t pid=0;uid_t uid;gid_t gid;
    if(surface && surface->resource)
        wl_client_get_credentials(wl_resource_get_client(surface->resource),&pid,&uid,&gid);
    return pid;
}
static struct weston_view* target_view(struct fixture* f,pid_t pid) {
    struct weston_view* view;struct weston_view* best=NULL;
    if(pid<=0)return NULL;
    wl_list_for_each(view,&f->compositor->view_list,link) {
        if(surface_pid(view->surface)!=pid || !weston_view_is_mapped(view) ||
           !view->surface->role_name || strcmp(view->surface->role_name,"xdg_toplevel"))continue;
        if(!best || (int64_t)view->surface->width*view->surface->height>
                    (int64_t)best->surface->width*best->surface->height)best=view;
    }
    return best;
}
static pid_t keyboard_pid(struct fixture* f) {
    return surface_pid(weston_seat_get_keyboard(&f->seat)->focus);
}
static pid_t pointer_pid(struct fixture* f) {
    struct weston_view* view=weston_seat_get_pointer(&f->seat)->focus;
    return view?surface_pid(view->surface):0;
}
static void reply(struct fixture* f,struct weston_view* view,const char* error) {
    char output[512];
    struct weston_pointer* pointer=weston_seat_get_pointer(&f->seat);
    struct weston_coord_surface local={0};
    if(view)local=weston_coord_global_to_surface(view,pointer->pos);
    snprintf(output,sizeof output,
        "{\"ok\":%s,\"error\":\"%s\",\"pid\":%d,\"width\":%d,\"height\":%d,"
        "\"keyboard_pid\":%d,\"pointer_pid\":%d,\"pointer_x\":%.9g,\"pointer_y\":%.9g,"
        "\"cursor_x\":%.9g,\"cursor_y\":%.9g}",
        error?"false":"true",error?error:"",view?surface_pid(view->surface):0,
        view?view->surface->width:0,view?view->surface->height:0,
        keyboard_pid(f),pointer_pid(f),pointer->pos.c.x,pointer->pos.c.y,local.c.x,local.c.y);
    if(send(f->fd,output,strlen(output),MSG_NOSIGNAL)<0)wl_display_terminate(f->compositor->wl_display);
}
static int command(int fd,uint32_t mask,void* data) {
    struct fixture* f=data;char line[256]={0},name[24]={0};int pid=0,a=0,b=0;double x=0,y=0;
    ssize_t count=recv(fd,line,sizeof line-1,0);
    if(count<=0 || mask&(WL_EVENT_HANGUP|WL_EVENT_ERROR)) {
        wl_display_terminate(f->compositor->wl_display);return 0;
    }
    if(sscanf(line,"%23s",name)!=1){reply(f,NULL,"empty command");return 0;}
    struct timespec time;clock_gettime(CLOCK_MONOTONIC,&time);
    if(!strcmp(name,"state")){reply(f,NULL,NULL);return 0;}
    if(!strcmp(name,"quit")){reply(f,NULL,NULL);wl_display_terminate(f->compositor->wl_display);return 0;}
    if(!strcmp(name,"motion")) {
        if(sscanf(line,"%*s %lf %lf",&x,&y)!=2 || !isfinite(x) || !isfinite(y) || fabs(x)>4096 || fabs(y)>4096) {
            reply(f,NULL,"invalid relative motion");return 0;
        }
        struct weston_pointer_motion_event event={.mask=WESTON_POINTER_MOTION_REL|WESTON_POINTER_MOTION_REL_UNACCEL,
            .rel=weston_coord(x,y),.rel_unaccel=weston_coord(x,y)};
        notify_motion(&f->seat,&time,&event);notify_pointer_frame(&f->seat);reply(f,NULL,NULL);return 0;
    }
    if(sscanf(line,"%*s %d",&pid)!=1){reply(f,NULL,"missing target pid");return 0;}
    if(!strcmp(name,"views")) {
        struct weston_view* item;
        wl_list_for_each(item,&f->compositor->view_list,link) {
            if(surface_pid(item->surface)==pid && weston_view_is_mapped(item))
                weston_log("Orbiter owned surface pid=%d role=%s size=%dx%d\n",pid,
                    item->surface->role_name?item->surface->role_name:"",item->surface->width,item->surface->height);
        }
        reply(f,NULL,NULL);return 0;
    }
    struct weston_view* view=target_view(f,pid);
    if(!view){reply(f,NULL,"owned surface not mapped");return 0;}
    if(!strcmp(name,"surface")){reply(f,view,NULL);return 0;}
    if(!strcmp(name,"focus")) {
        // A surface-to-surface transfer preserves the physical seat key set.
        // notify_keyboard_focus_out/in model backend device suspension instead.
        weston_seat_set_keyboard_focus(&f->seat,view->surface);
    } else if(!strcmp(name,"move")) {
        if(sscanf(line,"%*s %*d %lf %lf",&x,&y)!=2 || !isfinite(x) || !isfinite(y) ||
           x<0 || y<0 || x>=view->surface->width || y>=view->surface->height) {
            reply(f,view,"point outside owned surface");return 0;
        }
        struct weston_pointer* pointer=weston_seat_get_pointer(&f->seat);
        struct weston_coord_global position=weston_coord_surface_to_global(view,weston_coord_surface(x,y,view->surface));
        struct weston_pointer_motion_event event={.mask=WESTON_POINTER_MOTION_REL,
            .rel=weston_coord_global_sub(position,pointer->pos).c};
        notify_motion(&f->seat,&time,&event);notify_pointer_frame(&f->seat);
    } else if(!strcmp(name,"key")) {
        if(sscanf(line,"%*s %*d %d %d",&a,&b)!=2 || a<1 || a>255 || (b!=0 && b!=1) || keyboard_pid(f)!=pid) {
            reply(f,view,"invalid key or focus owner");return 0;
        }
        notify_key(&f->seat,&time,a,b?WL_KEYBOARD_KEY_STATE_PRESSED:WL_KEYBOARD_KEY_STATE_RELEASED,STATE_UPDATE_AUTOMATIC);
    } else if(!strcmp(name,"button")) {
        if(sscanf(line,"%*s %*d %d %d",&a,&b)!=2 || (a!=272 && a!=273) || (b!=0 && b!=1) || pointer_pid(f)!=pid) {
            reply(f,view,"invalid button or pointer owner");return 0;
        }
        notify_button(&f->seat,&time,a,b?WL_POINTER_BUTTON_STATE_PRESSED:WL_POINTER_BUTTON_STATE_RELEASED);
        notify_pointer_frame(&f->seat);
    } else if(!strcmp(name,"wheel")) {
        if(sscanf(line,"%*s %*d %d",&a)!=1 || (a!=-1 && a!=1) || pointer_pid(f)!=pid) {
            reply(f,view,"invalid wheel or pointer owner");return 0;
        }
        struct weston_pointer_axis_event event={.axis=WL_POINTER_AXIS_VERTICAL_SCROLL,.value=-10.*a,.has_discrete=true,.discrete=-a};
        notify_axis_source(&f->seat,WL_POINTER_AXIS_SOURCE_WHEEL);notify_axis(&f->seat,&time,&event);notify_pointer_frame(&f->seat);
    } else {reply(f,view,"unknown command");return 0;}
    reply(f,view,NULL);return 0;
}
static void destroy(struct wl_listener* listener,void* data) {
    (void)data;struct fixture* f=wl_container_of(listener,f,destroy);
    wl_list_remove(&f->destroy.link);
    wl_event_source_remove(f->source);weston_seat_release(&f->seat);close(f->fd);free(f);
}
WL_EXPORT int wet_module_init(struct weston_compositor* compositor,int* argc,char* argv[]) {
    (void)argc;(void)argv;
    const char* value=getenv("ORBITER_TEST_CONTROL_FD");const char* owner=getenv("ORBITER_TEST_CONTROLLER_PID");
    if(!value || !owner)return -1;
    int fd=atoi(value),type=0;struct ucred peer={0};socklen_t size=sizeof peer;
    if(getsockopt(fd,SOL_SOCKET,SO_PEERCRED,&peer,&size) || peer.pid!=atoi(owner) || peer.uid!=getuid())return -1;
    size=sizeof type;if(getsockopt(fd,SOL_SOCKET,SO_TYPE,&type,&size) || type!=SOCK_SEQPACKET)return -1;
    if(fcntl(fd,F_SETFD,FD_CLOEXEC)<0)return -1;
    unsetenv("ORBITER_TEST_CONTROL_FD");unsetenv("ORBITER_TEST_CONTROLLER_PID");
    struct fixture* f=calloc(1,sizeof *f);if(!f)return -1;
    f->compositor=compositor;f->fd=fd;
    weston_seat_init(&f->seat,compositor,"orbiter-owned-test-seat");
    if(weston_seat_init_pointer(&f->seat)<0 || weston_seat_init_keyboard(&f->seat,NULL)<0) {
        weston_seat_release(&f->seat);free(f);return -1;
    }
    f->source=wl_event_loop_add_fd(wl_display_get_event_loop(compositor->wl_display),fd,WL_EVENT_READABLE,command,f);
    if(!f->source){weston_seat_release(&f->seat);free(f);return -1;}
    f->destroy.notify=destroy;wl_signal_add(&compositor->destroy_signal,&f->destroy);
    reply(f,NULL,NULL);return 0;
}
