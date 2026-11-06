/* Display a native choice dialog. COBOL owns the score and business logic. */
#ifdef _WIN32
#include <windows.h>

int choose_score(void)
{
    return MessageBoxA(NULL, "Add one? Yes = add, No = subtract.",
                       "COBGDB GUI score", MB_YESNO | MB_ICONQUESTION) == IDYES;
}
#else
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>

int choose_score(void)
{
    Display *display = XOpenDisplay(NULL);
    if (!display) {
        fputs("The score example needs an X11 display.\n", stderr);
        exit(EXIT_FAILURE);
    }
    int screen = DefaultScreen(display);
    Window window = XCreateSimpleWindow(display, RootWindow(display, screen),
        40, 40, 320, 110, 1, BlackPixel(display, screen), WhitePixel(display, screen));
    XStoreName(display, window, "COBGDB GUI score");
    Atom close_window = XInternAtom(display, "WM_DELETE_WINDOW", False);
    XSetWMProtocols(display, window, &close_window, 1);
    XSelectInput(display, window, ExposureMask | ButtonPressMask);
    XMapWindow(display, window);
    GC gc = DefaultGC(display, screen);
    int choice = 0;
    for (;;) {
        XEvent event;
        XNextEvent(display, &event);
        if (event.type == Expose) {
            XDrawString(display, window, gc, 20, 25, "Choose a COBOL score operation", 30);
            XDrawRectangle(display, window, gc, 20, 45, 120, 45);
            XDrawRectangle(display, window, gc, 170, 45, 120, 45);
            XDrawString(display, window, gc, 55, 73, "Add one", 7);
            XDrawString(display, window, gc, 190, 73, "Subtract one", 12);
        } else if (event.type == ButtonPress && event.xbutton.y >= 45 && event.xbutton.y <= 90) {
            int x = event.xbutton.x;
            if ((x >= 20 && x <= 140) || (x >= 170 && x <= 290)) {
                choice = x <= 140;
                break;
            }
        } else if (event.type == ClientMessage && (Atom)event.xclient.data.l[0] == close_window) {
            break;
        }
    }
    XDestroyWindow(display, window);
    XCloseDisplay(display);
    return choice;
}
#endif
