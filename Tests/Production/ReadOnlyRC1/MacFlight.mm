// Hosted test only. Deliver the actual shortcut to Orbiter's Cocoa window.
#import <Cocoa/Cocoa.h>
#include <unistd.h>
#include <string.h>
__attribute__((constructor)) static void installFlightInput() {
    if (strcmp(getprogname(),"orbiter-production")!=0) return;
    dispatch_async(dispatch_get_main_queue(), ^{
        [NSTimer scheduledTimerWithTimeInterval:0.3 repeats:YES block:^(NSTimer *timer) {
            NSWindow *w = NSApp.keyWindow ?: NSApp.mainWindow;
            if (!w || !w.isVisible) return;
            NSString *title=w.title;
            if (![title containsString:@"RCS"] && ![title containsString:@"SPD"]) return;
            NSString *phase=NSProcessInfo.processInfo.environment[@"ORBITER_GUI_PHASE"];
            NSString *receipt=NSProcessInfo.processInfo.environment[@"ORBITER_GUI_RECEIPT"];
            NSString *dest=[receipt stringByAppendingString:@".window.txt"];
            [title writeToFile:dest atomically:YES encoding:NSUTF8StringEncoding error:nil];
            if ([phase isEqualToString:@"first"]) {
                for (NSNumber *kind in @[@(NSEventTypeKeyDown),@(NSEventTypeKeyUp)]) {
                    NSEvent *key=[NSEvent keyEventWithType:(NSEventType)kind.integerValue location:NSZeroPoint
                      modifierFlags:NSEventModifierFlagControl timestamp:NSProcessInfo.processInfo.systemUptime
                      windowNumber:w.windowNumber context:nil characters:@"s" charactersIgnoringModifiers:@"s"
                      isARepeat:NO keyCode:1];
                    [NSApp postEvent:key atStart:NO];
                }
            }
            [timer invalidate];
        }];
    });
}
