// Inject the real Cocoa keyboard events into the hosted flight's own window.
#import <Cocoa/Cocoa.h>
#include <string.h>
static void key(NSWindow *window, NSEventType type, unsigned short code, NSUInteger flags) {
    NSString *text = code==1 ? @"s" : @"";
    NSEvent *event=[NSEvent keyEventWithType:type location:NSZeroPoint modifierFlags:flags
        timestamp:NSProcessInfo.processInfo.systemUptime windowNumber:window.windowNumber
        context:nil characters:text charactersIgnoringModifiers:text isARepeat:NO keyCode:code];
    if(type==NSEventTypeFlagsChanged) [window.contentView flagsChanged:event];
    else if(type==NSEventTypeKeyDown) [window.contentView keyDown:event];
    else [window.contentView keyUp:event];
}
__attribute__((constructor)) static void installFlightInput() {
    if (strcmp(getprogname(),"orbiter-production")!=0) return;
    dispatch_async(dispatch_get_main_queue(), ^{
        __block bool sent=false;
        [NSTimer scheduledTimerWithTimeInterval:0.3 repeats:YES block:^(NSTimer *timer) {
            NSWindow *w = NSApp.keyWindow ?: NSApp.mainWindow;
            if (!w || !w.isVisible) return;
            NSString *title=w.title;
            if (![title containsString:@"RCS"] || ![title containsString:@"SPD"]) return;
            NSString *phase=NSProcessInfo.processInfo.environment[@"ORBITER_GUI_PHASE"];
            NSString *receipt=NSProcessInfo.processInfo.environment[@"ORBITER_GUI_RECEIPT"];
            if (!sent) {
                [title writeToFile:[receipt stringByAppendingString:@".window.txt"] atomically:YES encoding:NSUTF8StringEncoding error:nil];
                if ([phase isEqualToString:@"first"]) {
                    NSUInteger ctrl=NSEventModifierFlagControl | 1; // Include the left-device flag.
                    key(w,NSEventTypeFlagsChanged,59,ctrl);
                    key(w,NSEventTypeKeyDown,1,ctrl);
                    key(w,NSEventTypeKeyUp,1,ctrl);
                    key(w,NSEventTypeFlagsChanged,59,0);
                }
                sent=true;
            }
            if ([NSFileManager.defaultManager fileExistsAtPath:[receipt stringByAppendingString:@".close"]]) {
                [timer invalidate]; [w performClose:nil];
            }
        }];
    });
}
